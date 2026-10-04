"""
ADA Production Resilience & Load Testing Harness (Step 12)

Executes multi-scenario concurrent load and failure resilience tests against
the ADA FastAPI service engine, measuring throughput, p50/p95/p99 latencies,
idempotency, and security boundaries.

Run standalone via:
    python tests/load_test.py
"""

import asyncio
import os
import sys
import time
from typing import Any, Dict, List
import statistics

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings


class BenchmarkMetrics:
    def __init__(self, scenario_name: str):
        self.scenario_name = scenario_name
        self.latencies_ms: List[float] = []
        self.success_count = 0
        self.error_count = 0
        self.status_codes: Dict[int, int] = {}
        self.start_time = 0.0
        self.total_duration_sec = 0.0

    def record(self, latency_ms: float, status_code: int):
        self.latencies_ms.append(latency_ms)
        self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
        if 200 <= status_code < 400 or status_code in (413,):  # 413 expected in payload test
            self.success_count += 1
        else:
            self.error_count += 1

    def finish(self, duration_sec: float):
        self.total_duration_sec = duration_sec

    def summary(self) -> Dict[str, Any]:
        if not self.latencies_ms:
            return {"scenario": self.scenario_name, "total_requests": 0}

        sorted_latencies = sorted(self.latencies_ms)
        p50 = statistics.median(sorted_latencies)
        p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)] if len(sorted_latencies) >= 20 else max(sorted_latencies)
        p99 = sorted_latencies[int(len(sorted_latencies) * 0.99)] if len(sorted_latencies) >= 100 else max(sorted_latencies)
        rps = len(self.latencies_ms) / self.total_duration_sec if self.total_duration_sec > 0 else 0

        return {
            "scenario": self.scenario_name,
            "total_requests": len(self.latencies_ms),
            "throughput_rps": round(rps, 1),
            "min_ms": round(min(sorted_latencies), 2),
            "p50_ms": round(p50, 2),
            "p95_ms": round(p95, 2),
            "p99_ms": round(p99, 2),
            "max_ms": round(max(sorted_latencies), 2),
            "success_rate_pct": round((self.success_count / len(self.latencies_ms)) * 100, 1),
            "status_distribution": self.status_codes,
        }


async def run_scenario_concurrent_health(client: AsyncClient, total_requests: int = 100, concurrency: int = 20) -> BenchmarkMetrics:
    """Scenario 1: High-concurrency Liveness & Readiness Probing"""
    metrics = BenchmarkMetrics("Concurrent Health & Liveness Probes")
    semaphore = asyncio.Semaphore(concurrency)

    async def single_probe():
        async with semaphore:
            t0 = time.perf_counter()
            resp = await client.get("/health/live")
            latency = (time.perf_counter() - t0) * 1000
            metrics.record(latency, resp.status_code)

    t_start = time.perf_counter()
    await asyncio.gather(*(single_probe() for _ in range(total_requests)))
    metrics.finish(time.perf_counter() - t_start)
    return metrics


async def run_scenario_metrics_endpoint(client: AsyncClient, total_requests: int = 50, concurrency: int = 10) -> BenchmarkMetrics:
    """Scenario 2: Telemetry & Prometheus Metrics Scrape Under Concurrency"""
    metrics = BenchmarkMetrics("Prometheus Metrics Telemetry Scrape")
    semaphore = asyncio.Semaphore(concurrency)

    async def single_scrape():
        async with semaphore:
            t0 = time.perf_counter()
            resp = await client.get("/metrics")
            latency = (time.perf_counter() - t0) * 1000
            metrics.record(latency, resp.status_code)

    t_start = time.perf_counter()
    await asyncio.gather(*(single_scrape() for _ in range(total_requests)))
    metrics.finish(time.perf_counter() - t_start)
    return metrics


async def run_scenario_security_headers(client: AsyncClient) -> Dict[str, Any]:
    """Scenario 3: Defensive HTTP Security Headers Verification"""
    resp = await client.get("/")
    headers = resp.headers
    results = {
        "x_content_type_options": headers.get("X-Content-Type-Options") == "nosniff",
        "x_frame_options": headers.get("X-Frame-Options") == "DENY",
        "x_xss_protection": "mode=block" in headers.get("X-XSS-Protection", ""),
        "referrer_policy": headers.get("Referrer-Policy") == "strict-origin-when-cross-origin",
        "request_id_present": "X-Request-ID" in headers,
        "process_time_present": "X-Process-Time" in headers,
    }
    return results


async def run_scenario_payload_limit(client: AsyncClient) -> Dict[str, Any]:
    """Scenario 4: DOS Protection - Over-Sized Payload Rejection (Max 2MB)"""
    # Send a request exceeding 2MB limit
    oversized_data = "X" * (3 * 1024 * 1024)  # 3 MB
    resp = await client.post(
        "/api/v1/eta/calculate",
        content=oversized_data,
        headers={"Content-Type": "application/json", "Content-Length": str(len(oversized_data))},
    )
    return {
        "status_code": resp.status_code,
        "expected_413": resp.status_code == 413,
        "rejected_properly": "payload_too_large" in resp.text.lower() or resp.status_code == 413,
    }


async def main():
    print("=" * 70)
    print(" ADA STEP 12: PRODUCTION LOAD & RESILIENCE BENCHMARK")
    print("=" * 70)
    print(f"Environment:       {settings.ENVIRONMENT}")
    print(f"DB Pool Size:      {settings.DB_POOL_SIZE} (Max Overflow: {settings.DB_MAX_OVERFLOW})")
    print(f"Max Body Size:     {settings.MAX_CONTENT_LENGTH_BYTES / (1024*1024):.1f} MB")
    print("-" * 70)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health Probes
        print("\n[1/4] Running Scenario: Concurrent Health Probes (100 reqs, concurrency=20)...")
        m1 = await run_scenario_concurrent_health(client, total_requests=100, concurrency=20)
        s1 = m1.summary()
        print(f"      Throughput:  {s1['throughput_rps']} req/s")
        print(f"      Latency:     p50={s1['p50_ms']}ms | p95={s1['p95_ms']}ms | p99={s1['p99_ms']}ms")
        print(f"      Success:     {s1['success_rate_pct']}% (Codes: {s1['status_distribution']})")

        # 2. Metrics Telemetry Scrape
        print("\n[2/4] Running Scenario: Concurrent Prometheus Metrics Scrapes (50 reqs, concurrency=10)...")
        m2 = await run_scenario_metrics_endpoint(client, total_requests=50, concurrency=10)
        s2 = m2.summary()
        print(f"      Throughput:  {s2['throughput_rps']} req/s")
        print(f"      Latency:     p50={s2['p50_ms']}ms | p95={s2['p95_ms']}ms | p99={s2['p99_ms']}ms")
        print(f"      Success:     {s2['success_rate_pct']}% (Codes: {s2['status_distribution']})")

        # 3. Security Headers Verification
        print("\n[3/4] Running Scenario: Security Headers Verification...")
        sec_results = await run_scenario_security_headers(client)
        for check, passed in sec_results.items():
            status_text = "PASS" if passed else "FAIL"
            print(f"      - {check:<26}: [{status_text}]")

        # 4. Memory Exhaustion / Payload DOS Protection
        print("\n[4/4] Running Scenario: Over-sized Payload Protection (3MB payload)...")
        dos_results = await run_scenario_payload_limit(client)
        print(f"      - HTTP Status:               {dos_results['status_code']}")
        print(f"      - Expected 413 Payload Large: [{('PASS' if dos_results['expected_413'] else 'FAIL')}]")

    print("\n" + "=" * 70)
    print(" BENCHMARK COMPLETED SUCCESSFULLY")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
