/**
 * ADA Mobile Local Notification Service.
 * Manages native local notifications with stable IDs to prevent duplicate alerts.
 */

let NotificationsModule: any = null;
try {
  NotificationsModule = require("expo-notifications");
} catch {
  // Expo notifications module not available in node/test runtime
}

export class NotificationManager {
  static async requestPermissions(): Promise<boolean> {
    if (!NotificationsModule?.requestPermissionsAsync) return true;
    const { status } = await NotificationsModule.requestPermissionsAsync();
    return status === "granted";
  }

  static async notifyTrackingStarted(journeyTitle: string): Promise<string | null> {
    if (!NotificationsModule?.scheduleNotificationAsync) return "mock-tracking-id";
    return await NotificationsModule.scheduleNotificationAsync({
      identifier: `tracking-start-${Date.now()}`,
      content: {
        title: "Journey Tracking Active",
        body: `Monitoring travel progress to ${journeyTitle}.`,
        sound: "default",
        priority: "high",
      },
      trigger: null, // Immediate
    });
  }

  static async notifyApproaching(journeyTitle: string, distanceMeters: number): Promise<string | null> {
    if (!NotificationsModule?.scheduleNotificationAsync) return "mock-approaching-id";
    return await NotificationsModule.scheduleNotificationAsync({
      identifier: `approaching-${journeyTitle}`,
      content: {
        title: "Approaching Destination",
        body: `You are approximately ${(distanceMeters / 1000).toFixed(1)} km from ${journeyTitle}.`,
        sound: "default",
        priority: "high",
      },
      trigger: null,
    });
  }

  static async notifyArrival(journeyTitle: string): Promise<string | null> {
    if (!NotificationsModule?.scheduleNotificationAsync) return "mock-arrival-id";
    return await NotificationsModule.scheduleNotificationAsync({
      identifier: `arrival-${journeyTitle}`,
      content: {
        title: "Destination Reached! 🎯",
        body: `You have successfully arrived at ${journeyTitle}. Tracking concluded.`,
        sound: "alarm.wav",
        priority: "max",
      },
      trigger: null,
    });
  }

  static async cancelNotification(identifier: string): Promise<void> {
    if (!NotificationsModule?.cancelScheduledNotificationAsync) return;
    await NotificationsModule.cancelScheduledNotificationAsync(identifier);
  }
}
