import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithPopup,
  signOut as firebaseSignOut,
  sendPasswordResetEmail,
  updateProfile,
  User as FirebaseUser,
  AuthError,
} from "firebase/auth";
import { auth, googleProvider } from "./config";

/**
 * Maps Firebase Authentication error codes to clean, user-friendly ADA messages.
 * Prevents raw SDK error strings or internal security stack details from reaching the UI.
 */
export function mapFirebaseAuthError(error: unknown): string {
  if (!error || typeof error !== "object") {
    return "An unexpected authentication error occurred. Please try again.";
  }

  const code = (error as AuthError).code || "";

  switch (code) {
    case "auth/invalid-credential":
    case "auth/user-not-found":
    case "auth/wrong-password":
      return "Invalid email or password. Please verify your credentials.";

    case "auth/email-already-in-use":
      return "This email address is already registered. Please sign in instead.";

    case "auth/weak-password":
      return "Password must be at least 6 characters long and meet required security rules.";

    case "auth/invalid-email":
      return "Please enter a valid email address.";

    case "auth/popup-closed-by-user":
      return "Google sign-in was cancelled before completion.";

    case "auth/popup-blocked":
      return "Sign-in popup was blocked by your browser. Please allow popups for this site.";

    case "auth/network-request-failed":
      return "Network connection unavailable. Please check your internet connection.";

    case "auth/too-many-requests":
      return "Access temporarily disabled due to too many failed attempts. Try again later or reset password.";

    case "auth/user-disabled":
      return "This account has been disabled. Please contact support.";

    case "auth/account-exists-with-different-credential":
      return "An account already exists with this email using a different sign-in provider.";

    case "auth/requires-recent-login":
      return "This operation is sensitive. Please re-authenticate and try again.";

    default:
      return (error as Error).message || "Unable to complete authentication right now. Please try again.";
  }
}

/**
 * Signs in with Google using popup flow.
 */
export async function loginWithGoogle(): Promise<FirebaseUser> {
  const result = await signInWithPopup(auth, googleProvider);
  return result.user;
}

/**
 * Signs in with Email and Password.
 */
export async function loginWithEmail(email: string, pass: string): Promise<FirebaseUser> {
  const result = await signInWithEmailAndPassword(auth, email.trim(), pass);
  return result.user;
}

/**
 * Registers a new user with Email and Password, and updates their display name.
 */
export async function registerWithEmail(
  email: string,
  pass: string,
  displayName?: string
): Promise<FirebaseUser> {
  const result = await createUserWithEmailAndPassword(auth, email.trim(), pass);
  if (displayName && displayName.trim()) {
    await updateProfile(result.user, { displayName: displayName.trim() });
  }
  return result.user;
}

/**
 * Sends a password reset email.
 */
export async function requestPasswordReset(email: string): Promise<void> {
  await sendPasswordResetEmail(auth, email.trim());
}

/**
 * Signs out the current Firebase user.
 */
export async function logoutUser(): Promise<void> {
  await firebaseSignOut(auth);
}
