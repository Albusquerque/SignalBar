export type LightEvent = "notification" | "achievement" | "screenshot" | "record-start" | "record-stop";

// SteamClient.Notifications EClientNotificationType values in @decky/ui.
// Only events with dedicated patterns are special; every other valid Steam
// notification, including Community comments and future types, gets a signal.

export function classifySteamNotification(type: number): LightEvent | null {
  if (!Number.isSafeInteger(type) || type <= 0) return null;
  if (type === 5) return "achievement";
  if (type === 14) return "screenshot";
  if (type === 55) return "record-start";
  if (type === 56) return "record-stop";
  return "notification";
}

export function screenshotWasCaptured(notification: { strOperation?: string } | null | undefined): boolean {
  return notification?.strOperation === "written";
}
