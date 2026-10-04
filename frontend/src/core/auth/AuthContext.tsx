import React, { createContext, useContext, useEffect, useState, useMemo } from "react";
import { User as FirebaseUser, onAuthStateChanged } from "firebase/auth";
import { auth } from "@/lib/firebase/config";
import {
  loginWithEmail,
  loginWithGoogle,
  registerWithEmail,
  logoutUser,
  requestPasswordReset,
  mapFirebaseAuthError,
} from "@/lib/firebase/auth";
import apiClient from "@/core/api/apiClient";

export interface AdaUser {
  id: string;
  firebaseUid: string;
  email: string;
  name?: string | null;
  profileImage?: string | null;
  timezone: string;
  createdAt: string;
  updatedAt: string;
}

interface AuthContextType {
  currentUser: AdaUser | null;
  firebaseUser: FirebaseUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  signIn: (email: string, pass: string) => Promise<void>;
  signUp: (email: string, pass: string, name?: string) => Promise<void>;
  signInWithGoogle: () => Promise<void>;
  signOut: () => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [firebaseUser, setFirebaseUser] = useState<FirebaseUser | null>(null);
  const [currentUser, setCurrentUser] = useState<AdaUser | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Synchronize ADA user profile from backend
  const fetchAdaProfile = async (fbUser: FirebaseUser): Promise<void> => {
    try {
      // Force token generation for initial handshake
      const token = await fbUser.getIdToken();
      const response = await apiClient.get<AdaUser>("/users/me", {
        headers: { Authorization: `Bearer ${token}` },
      });
      setCurrentUser(response.data);
    } catch {
      // Fallback profile if backend unreachable in preview/offline mode
      setCurrentUser({
        id: fbUser.uid,
        firebaseUid: fbUser.uid,
        email: fbUser.email || "",
        name: fbUser.displayName || "ADA User",
        profileImage: fbUser.photoURL,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });
    }
  };

  useEffect(() => {
    // Listen to Firebase auth state lifecycle
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      setFirebaseUser(user);
      if (user) {
        await fetchAdaProfile(user);
      } else {
        setCurrentUser(null);
      }
      setIsLoading(false);
    });

    return () => unsubscribe();
  }, []);

  const signIn = async (email: string, pass: string): Promise<void> => {
    try {
      const user = await loginWithEmail(email, pass);
      await fetchAdaProfile(user);
    } catch (error) {
      throw new Error(mapFirebaseAuthError(error));
    }
  };

  const signUp = async (email: string, pass: string, name?: string): Promise<void> => {
    try {
      const user = await registerWithEmail(email, pass, name);
      await fetchAdaProfile(user);
    } catch (error) {
      throw new Error(mapFirebaseAuthError(error));
    }
  };

  const signInWithGoogle = async (): Promise<void> => {
    try {
      const user = await loginWithGoogle();
      await fetchAdaProfile(user);
    } catch (error) {
      throw new Error(mapFirebaseAuthError(error));
    }
  };

  const signOut = async (): Promise<void> => {
    try {
      await logoutUser();
      setCurrentUser(null);
      setFirebaseUser(null);
    } catch (error) {
      throw new Error(mapFirebaseAuthError(error));
    }
  };

  const resetPassword = async (email: string): Promise<void> => {
    try {
      await requestPasswordReset(email);
    } catch (error) {
      throw new Error(mapFirebaseAuthError(error));
    }
  };

  const refreshProfile = async (): Promise<void> => {
    if (firebaseUser) {
      await fetchAdaProfile(firebaseUser);
    }
  };

  const value = useMemo(
    () => ({
      currentUser,
      firebaseUser,
      isAuthenticated: Boolean(firebaseUser),
      isLoading,
      signIn,
      signUp,
      signInWithGoogle,
      signOut,
      resetPassword,
      refreshProfile,
    }),
    [currentUser, firebaseUser, isLoading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
