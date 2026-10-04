/**
 * Web Push and browser notification management utility.
 * Handles permission requests, service worker registration, and PushManager subscription.
 */

export function isPushSupported(): boolean {
  return (
    typeof window !== 'undefined' &&
    'serviceWorker' in navigator &&
    'PushManager' in window &&
    'Notification' in window
  );
}

export function getNotificationPermission(): NotificationPermission {
  if (typeof window === 'undefined' || !('Notification' in window)) {
    return 'default';
  }
  return Notification.permission;
}

export async function requestNotificationPermission(): Promise<NotificationPermission> {
  if (!('Notification' in window)) {
    return 'denied';
  }
  return await Notification.requestPermission();
}

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

export async function subscribeToWebPush(
  vapidPublicKey: string
): Promise<{ endpoint: string; p256dh: string; auth: string; userAgent: string } | null> {
  if (!isPushSupported()) return null;

  const reg = await navigator.serviceWorker.ready;
  if (!reg.pushManager) return null;

  const convertedKey = urlBase64ToUint8Array(vapidPublicKey);
  const subscription = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: convertedKey as unknown as BufferSource,
  });

  const rawKey = subscription.getKey('p256dh');
  const rawAuth = subscription.getKey('auth');

  const p256dh = rawKey
    ? btoa(String.fromCharCode.apply(null, Array.from(new Uint8Array(rawKey))))
    : '';
  const auth = rawAuth
    ? btoa(String.fromCharCode.apply(null, Array.from(new Uint8Array(rawAuth))))
    : '';

  return {
    endpoint: subscription.endpoint,
    p256dh,
    auth,
    userAgent: navigator.userAgent,
  };
}

export async function unsubscribeFromWebPush(): Promise<string | null> {
  if (!isPushSupported()) return null;

  const reg = await navigator.serviceWorker.ready;
  const subscription = await reg.pushManager.getSubscription();
  if (subscription) {
    const endpoint = subscription.endpoint;
    await subscription.unsubscribe();
    return endpoint;
  }
  return null;
}
