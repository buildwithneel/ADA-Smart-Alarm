import { describe, expect, it } from "vitest";
import { AdaApiClient, getDefaultBaseUrl } from "../src/api/apiClient.js";

describe("AdaApiClient Configuration & Networking Suite", () => {
  it("resolves default development base URL", () => {
    const url = getDefaultBaseUrl();
    expect(url).toContain("/api/v1");
  });

  it("initializes API client with custom base URL", () => {
    const client = new AdaApiClient("https://api.ada-alarm.app/api/v1");
    expect(client).toBeDefined();
  });
});
