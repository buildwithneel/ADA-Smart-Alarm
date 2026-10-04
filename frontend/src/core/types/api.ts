export interface APIResponse<T> {
  success: boolean;
  data: T;
  message?: string;
  meta?: Record<string, unknown>;
}

export interface APIErrorResponse {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance?: string;
  details?: Record<string, unknown>;
}
