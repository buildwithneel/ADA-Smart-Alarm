/**
 * Secure Token Storage for ADA Mobile.
 * Stores JWT / Firebase ID tokens in hardware-backed keystore (iOS Keychain / Android KeyStore).
 * Never stores credentials in plaintext AsyncStorage.
 */

const TOKEN_KEY = "ada_auth_id_token";
const REFRESH_TOKEN_KEY = "ada_auth_refresh_token";

// Memory storage fallback for testing and non-native environments
const memoryStore = new Map<string, string>();

let SecureStoreModule: any = null;
try {
  SecureStoreModule = require("expo-secure-store");
} catch {
  // Expo SecureStore not available in node/test runtime; fallback to memoryStore
}

export class TokenStorage {
  static async setToken(token: string): Promise<void> {
    if (SecureStoreModule?.setItemAsync) {
      await SecureStoreModule.setItemAsync(TOKEN_KEY, token, {
        keychainAccessible: SecureStoreModule.AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY,
      });
    } else {
      memoryStore.set(TOKEN_KEY, token);
    }
  }

  static async getToken(): Promise<string | null> {
    if (SecureStoreModule?.getItemAsync) {
      return await SecureStoreModule.getItemAsync(TOKEN_KEY);
    }
    return memoryStore.get(TOKEN_KEY) ?? null;
  }

  static async setRefreshToken(refreshToken: string): Promise<void> {
    if (SecureStoreModule?.setItemAsync) {
      await SecureStoreModule.setItemAsync(REFRESH_TOKEN_KEY, refreshToken, {
        keychainAccessible: SecureStoreModule.AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY,
      });
    } else {
      memoryStore.set(REFRESH_TOKEN_KEY, refreshToken);
    }
  }

  static async getRefreshToken(): Promise<string | null> {
    if (SecureStoreModule?.getItemAsync) {
      return await SecureStoreModule.getItemAsync(REFRESH_TOKEN_KEY);
    }
    return memoryStore.get(REFRESH_TOKEN_KEY) ?? null;
  }

  static async clearAll(): Promise<void> {
    if (SecureStoreModule?.deleteItemAsync) {
      await SecureStoreModule.deleteItemAsync(TOKEN_KEY);
      await SecureStoreModule.deleteItemAsync(REFRESH_TOKEN_KEY);
    }
    memoryStore.clear();
  }
}
