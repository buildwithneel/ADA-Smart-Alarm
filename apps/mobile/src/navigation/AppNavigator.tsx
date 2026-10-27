/**
 * ADA Mobile App Navigator.
 * Simple, resilient screen switcher handling Auth, Home, Create, Details, Diagnostics, and Settings.
 */

import React, { useEffect, useState } from "react";
import { SafeAreaView, StatusBar, StyleSheet, View } from "react-native";
import { AdaApiClient } from "../api/apiClient.js";
import { TokenStorage } from "../auth/tokenStorage.js";
import { AuthScreen } from "../screens/AuthScreen.js";
import { CreateEditJourneyScreen } from "../screens/CreateEditJourneyScreen.js";
import { DiagnosticsScreen } from "../screens/DiagnosticsScreen.js";
import { HomeScreen } from "../screens/HomeScreen.js";
import { JourneyDetailScreen } from "../screens/JourneyDetailScreen.js";
import { SettingsScreen } from "../screens/SettingsScreen.js";
import { colors } from "../theme/theme.js";

type Screen = "AUTH" | "HOME" | "CREATE" | "DETAIL" | "DIAGNOSTICS" | "SETTINGS";

export const AppNavigator: React.FC = () => {
  const [currentScreen, setCurrentScreen] = useState<Screen>("AUTH");
  const [selectedJourneyId, setSelectedJourneyId] = useState<string | null>(null);
  const [apiClient] = useState(() => new AdaApiClient());

  useEffect(() => {
    // Check if session token exists in SecureStore
    TokenStorage.getToken().then((token) => {
      if (token) {
        setCurrentScreen("HOME");
      }
    });
  }, []);

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="light-content" backgroundColor={colors.background} />
      <View style={styles.container}>
        {currentScreen === "AUTH" && (
          <AuthScreen
            onAuthSuccess={() => setCurrentScreen("HOME")}
            onContinueOffline={() => setCurrentScreen("HOME")}
          />
        )}

        {currentScreen === "HOME" && (
          <HomeScreen
            apiClient={apiClient}
            onNavigateToJourney={(id) => {
              setSelectedJourneyId(id);
              setCurrentScreen("DETAIL");
            }}
            onNavigateToCreate={() => setCurrentScreen("CREATE")}
            onNavigateToDiagnostics={() => setCurrentScreen("DIAGNOSTICS")}
            onNavigateToSettings={() => setCurrentScreen("SETTINGS")}
          />
        )}

        {currentScreen === "CREATE" && (
          <CreateEditJourneyScreen
            apiClient={apiClient}
            onBack={() => setCurrentScreen("HOME")}
            onSuccess={() => setCurrentScreen("HOME")}
          />
        )}

        {currentScreen === "DETAIL" && selectedJourneyId && (
          <JourneyDetailScreen
            journeyId={selectedJourneyId}
            apiClient={apiClient}
            onBack={() => setCurrentScreen("HOME")}
          />
        )}

        {currentScreen === "DIAGNOSTICS" && (
          <DiagnosticsScreen onBack={() => setCurrentScreen("HOME")} />
        )}

        {currentScreen === "SETTINGS" && (
          <SettingsScreen
            onBack={() => setCurrentScreen("HOME")}
            onSignOut={() => setCurrentScreen("AUTH")}
          />
        )}
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: colors.background,
  },
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
});
