import { beforeEach, describe, expect, it } from "vitest";
import { TokenStorage } from "../src/auth/tokenStorage.js";

describe("TokenStorage Security Suite", () => {
  beforeEach(async () => {
    await TokenStorage.clearAll();
  });

  it("stores and retrieves auth ID token", async () => {
    expect(await TokenStorage.getToken()).toBeNull();

    const sampleToken = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.sample_payload.signature";
    await TokenStorage.setToken(sampleToken);

    expect(await TokenStorage.getToken()).toBe(sampleToken);
  });

  it("stores and retrieves refresh token", async () => {
    const refreshToken = "refresh-token-xyz-123";
    await TokenStorage.setRefreshToken(refreshToken);

    expect(await TokenStorage.getRefreshToken()).toBe(refreshToken);
  });

  it("clears all stored credentials safely", async () => {
    await TokenStorage.setToken("token-to-clear");
    await TokenStorage.setRefreshToken("refresh-to-clear");

    await TokenStorage.clearAll();

    expect(await TokenStorage.getToken()).toBeNull();
    expect(await TokenStorage.getRefreshToken()).toBeNull();
  });
});
