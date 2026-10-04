import { z } from "zod";

const envSchema = z.object({
  VITE_API_BASE_URL: z.string().url().default("http://localhost:8000/api/v1"),
  VITE_FIREBASE_API_KEY: z.string().min(1).default("mock-api-key-for-dev"),
  VITE_FIREBASE_AUTH_DOMAIN: z.string().min(1).default("ada-alarm.firebaseapp.com"),
  VITE_FIREBASE_PROJECT_ID: z.string().min(1).default("ada-dynamic-alarm"),
  VITE_FIREBASE_STORAGE_BUCKET: z.string().optional(),
  VITE_FIREBASE_MESSAGING_SENDER_ID: z.string().optional(),
  VITE_FIREBASE_APP_ID: z.string().optional(),
  VITE_GOOGLE_MAPS_API_KEY: z.string().optional(),
  VITE_MAPBOX_ACCESS_TOKEN: z.string().optional(),
  VITE_MAP_PROVIDER: z.enum(["google", "mapbox"]).default("mapbox"),
  VITE_ROUTING_PROVIDER: z.enum(["google", "mapbox"]).default("google"),
  VITE_GEOCODING_PROVIDER: z.enum(["google", "mapbox"]).default("google"),
  VITE_TRAFFIC_PROVIDER: z.enum(["google", "mapbox"]).default("google"),
  VITE_ENABLE_MAP_FALLBACK: z.string().optional().transform((v) => v !== "false"),
  VITE_APP_ENV: z.enum(["development", "staging", "production"]).default("development"),
});

const parsedEnv = envSchema.safeParse(import.meta.env);

if (!parsedEnv.success) {
  console.error("❌ Invalid environment variables configuration:", parsedEnv.error.format());
  throw new Error("Invalid frontend environment variables. Check .env configuration.");
}

export const env = parsedEnv.data;
