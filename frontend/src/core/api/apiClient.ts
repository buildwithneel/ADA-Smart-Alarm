import axios, { AxiosInstance, InternalAxiosRequestConfig } from "axios";
import { auth } from "@/lib/firebase/config";

// Create configured Axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || "/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 10000, // 10 seconds timeout
});

// Request interceptor injecting fresh Firebase ID tokens dynamically
apiClient.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    try {
      const currentUser = auth.currentUser;
      if (currentUser) {
        // Retrieve fresh ID token (false = return cached if valid, refreshes if expired)
        const token = await currentUser.getIdToken(false);
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch (err) {
      console.warn("Unable to inject Firebase ID token:", err);
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for centralized error interception
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const status = error.response.status;
      const detail = error.response.data?.detail || "An unexpected error occurred.";

      switch (status) {
        case 401:
          console.warn("Unauthorized access: Access token may have expired or is invalid.", detail);
          break;
        case 403:
          console.error("Forbidden action: User lacks permissions.", detail);
          break;
        case 500:
          console.error("Internal Server Error: Backend failed.", detail);
          break;
        default:
          console.error(`API Error [${status}]:`, detail);
      }
    } else if (error.request) {
      console.error("Network Error: No response received from server. Check backend status.");
    } else {
      console.error("Request Configuration Error:", error.message);
    }
    return Promise.reject(error);
  }
);

export default apiClient;
