/**
 * ADA Mobile Typed API Client.
 * Communicates with FastAPI backend services (`/api/v1`) using token injection,
 * automatic retry on 401, idempotency key support, and typed DTOs.
 */

import axios, { AxiosInstance, InternalAxiosRequestConfig } from "axios";
import {
  AlarmCreateDto,
  AlarmDto,
  AlarmUpdateDto,
  DestinationCreateDto,
  DestinationDto,
  RouteRequestDto,
  RouteResultDto,
  UserDto,
} from "@ada/shared";
import { TokenStorage } from "../auth/tokenStorage.js";

export function getDefaultBaseUrl(): string {
  if (process.env.EXPO_PUBLIC_API_URL) {
    return process.env.EXPO_PUBLIC_API_URL;
  }
  // Default to localhost:8000 for local development
  return "http://localhost:8000/api/v1";
}

export class AdaApiClient {
  private client: AxiosInstance;
  private onTokenRefreshNeeded?: () => Promise<string | null>;

  constructor(baseURL?: string, onTokenRefresh?: () => Promise<string | null>) {
    this.onTokenRefreshNeeded = onTokenRefresh;
    this.client = axios.create({
      baseURL: baseURL || getDefaultBaseUrl(),
      timeout: 10000,
      headers: {
        "Content-Type": "application/json",
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors(): void {
    // Inject Authorization header
    this.client.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
      const token = await TokenStorage.getToken();
      if (token && !config.headers.Authorization) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Handle 401 refresh retry
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;
        if (error.response?.status === 401 && !originalRequest._retry && this.onTokenRefreshNeeded) {
          originalRequest._retry = true;
          try {
            const newToken = await this.onTokenRefreshNeeded();
            if (newToken) {
              await TokenStorage.setToken(newToken);
              originalRequest.headers.Authorization = `Bearer ${newToken}`;
              return this.client(originalRequest);
            }
          } catch (refreshErr) {
            await TokenStorage.clearAll();
            return Promise.reject(refreshErr);
          }
        }
        return Promise.reject(error);
      }
    );
  }

  // --- Users ---
  async getCurrentUser(): Promise<UserDto> {
    const res = await this.client.get<UserDto>("/users/me");
    return res.data;
  }

  // --- Destinations ---
  async getDestinations(skip = 0, limit = 100): Promise<DestinationDto[]> {
    const res = await this.client.get<DestinationDto[]>("/destinations", {
      params: { skip, limit },
    });
    return res.data;
  }

  async createDestination(data: DestinationCreateDto): Promise<DestinationDto> {
    const res = await this.client.post<DestinationDto>("/destinations", data);
    return res.data;
  }

  // --- Alarms / Journeys ---
  async getAlarms(status?: string, filter?: string, skip = 0, limit = 100): Promise<AlarmDto[]> {
    const res = await this.client.get<AlarmDto[]>("/alarms", {
      params: { status, filter, skip, limit },
    });
    return res.data;
  }

  async createAlarm(data: AlarmCreateDto, idempotencyKey?: string): Promise<AlarmDto> {
    const headers: Record<string, string> = {};
    if (idempotencyKey) {
      headers["X-Idempotency-Key"] = idempotencyKey;
    }
    const res = await this.client.post<AlarmDto>("/alarms", data, { headers });
    return res.data;
  }

  async getAlarm(id: string): Promise<AlarmDto> {
    const res = await this.client.get<AlarmDto>(`/alarms/${id}`);
    return res.data;
  }

  async updateAlarm(id: string, data: AlarmUpdateDto): Promise<AlarmDto> {
    const res = await this.client.patch<AlarmDto>(`/alarms/${id}`, data);
    return res.data;
  }

  async deleteAlarm(id: string): Promise<void> {
    await this.client.delete(`/alarms/${id}`);
  }

  async enableAlarm(id: string): Promise<AlarmDto> {
    const res = await this.client.post<AlarmDto>(`/alarms/${id}/enable`);
    return res.data;
  }

  async disableAlarm(id: string): Promise<AlarmDto> {
    const res = await this.client.post<AlarmDto>(`/alarms/${id}/disable`);
    return res.data;
  }

  // --- Routing & Live Traffic ---
  async calculateRoute(data: RouteRequestDto): Promise<RouteResultDto> {
    const res = await this.client.post<RouteResultDto>("/routes", data);
    return res.data;
  }
}
