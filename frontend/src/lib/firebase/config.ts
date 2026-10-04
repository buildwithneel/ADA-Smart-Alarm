import { initializeApp, getApps, getApp, FirebaseApp } from "firebase/app";
import {
  getAuth,
  GoogleAuthProvider,
  Auth,
  browserLocalPersistence,
  setPersistence,
} from "firebase/auth";

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || "AIzaSyDummyKeyForDevelopmentPreview",
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || "ada-dynamic-alarm.firebaseapp.com",
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || "ada-dynamic-alarm",
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || "ada-dynamic-alarm.appspot.com",
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || "123456789012",
  appId: import.meta.env.VITE_FIREBASE_APP_ID || "1:123456789012:web:abcdef1234567890",
};

// Singleton Firebase Application Initialization
export const firebaseApp: FirebaseApp = !getApps().length
  ? initializeApp(firebaseConfig)
  : getApp();

// Centralized Firebase Auth Instance
export const auth: Auth = getAuth(firebaseApp);

// Configure persistent local storage session
setPersistence(auth, browserLocalPersistence).catch((err) => {
  console.warn("Failed to set Firebase Auth persistence to browserLocalPersistence:", err);
});

// Configure Authentication Providers
export const googleProvider = new GoogleAuthProvider();
googleProvider.setCustomParameters({ prompt: "select_account" });
