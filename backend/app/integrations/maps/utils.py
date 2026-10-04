from __future__ import annotations

import math
from typing import Dict, List, Tuple


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates great-circle distance between two GPS coordinates in meters using Haversine formula.
    """
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def estimate_speed_meters_per_sec(mode: str) -> float:
    """Average mode speed in meters per second for realistic duration estimation."""
    speeds = {
        "driving": 13.88,  # ~50 km/h
        "transit": 8.33,   # ~30 km/h
        "cycling": 4.16,   # ~15 km/h
        "walking": 1.25,   # ~4.5 km/h
    }
    return speeds.get(mode, 13.88)


def create_simple_encoded_polyline(points: List[Tuple[float, float]]) -> str:
    """
    Creates a standard Google/Mapbox encoded polyline string from coordinate tuples (lat, lng).
    Implements the standard polyline algorithm.
    """
    result: List[str] = []
    prev_lat = 0
    prev_lng = 0

    for lat, lng in points:
        lat_e5 = int(round(lat * 1e5))
        lng_e5 = int(round(lng * 1e5))

        d_lat = lat_e5 - prev_lat
        d_lng = lng_e5 - prev_lng

        prev_lat = lat_e5
        prev_lng = lng_e5

        for val in (d_lat, d_lng):
            val = ~(val << 1) if val < 0 else (val << 1)
            while val >= 0x20:
                result.append(chr((0x20 | (val & 0x1F)) + 63))
                val >>= 5
            result.append(chr(val + 63))

    return "".join(result)


def format_duration_seconds(seconds: int) -> str:
    """Formats seconds into human-readable e.g. '38 min', '1 hr 15 min'."""
    mins = int(round(seconds / 60))
    if mins < 60:
        return f"{mins} min"
    hours = mins // 60
    remaining_mins = mins % 60
    if remaining_mins == 0:
        return f"{hours} hr"
    return f"{hours} hr {remaining_mins} min"


def format_distance_meters(meters: int) -> str:
    """Formats meters into e.g. '800 m' or '12.4 km'."""
    if meters < 1000:
        return f"{meters} m"
    km = meters / 1000.0
    return f"{km:.1f} km"


def calculate_congestion_level(delay_seconds: int) -> str:
    """Categorizes traffic delay into low, moderate, heavy, or severe."""
    if delay_seconds <= 120:
        return "low"
    elif delay_seconds <= 600:
        return "moderate"
    elif delay_seconds <= 1200:
        return "heavy"
    return "severe"
