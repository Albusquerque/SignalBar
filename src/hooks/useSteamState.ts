import { useEffect } from "react";
import { Router } from "@decky/ui";
import { gameChanged, setSteamActivity } from "../api";

declare const SteamClient: any;
declare const appStore: any;

function normalizeAppId(value: unknown): number {
  const number = Number(value ?? 0);
  return Number.isFinite(number) && number > 0 ? Math.trunc(number) : 0;
}

function runningApp() {
  try {
    const app: any = Router?.MainRunningApp;
    const appid = normalizeAppId(app?.appid ?? app?.appID ?? app?.unAppID ?? app?.app_id);
    const title = String(app?.display_name ?? app?.name ?? "");
    return { appid, title };
  } catch {
    return { appid: 0, title: "" };
  }
}

function titleFor(appid: number): string {
  try {
    return String(appStore?.GetAppOverviewByAppID?.(appid)?.display_name ?? "");
  } catch {
    return "";
  }
}

export function useSteamState(onGame: (appid: number, title: string) => void) {
  useEffect(() => {
    let alive = true;
    let lastKey = "";
    const report = (appid: number, title: string) => {
      if (!alive) return;
      const key = `${appid}:${title}`;
      if (key === lastKey) return;
      lastKey = key;
      void gameChanged(appid, title).then(() => onGame(appid, title)).catch(console.warn);
    };

    const poll = window.setInterval(() => {
      const app = runningApp();
      report(app.appid, app.title);
    }, 2000);
    const initial = runningApp();
    report(initial.appid, initial.title);

    let gameRegistration: any;
    let downloadRegistration: any;
    try {
      gameRegistration = SteamClient?.GameSessions?.RegisterForAppLifetimeNotifications?.((event: any) => {
        if (event?.bRunning) {
          const appid = normalizeAppId(event?.unAppID);
          report(appid, titleFor(appid) || runningApp().title);
        } else {
          const current = runningApp();
          report(current.appid, current.title);
        }
      });
    } catch (error) {
      console.warn("[SignalBar] Steam game hook unavailable", error);
    }
    try {
      downloadRegistration = SteamClient?.Downloads?.RegisterForDownloadItemsChanged?.(() => {
        // Any native download transition gets a renewable conservative lease.
        void setSteamActivity(true, "Steam download activity").catch(console.warn);
      });
    } catch (error) {
      console.warn("[SignalBar] Steam download hook unavailable", error);
    }

    return () => {
      alive = false;
      window.clearInterval(poll);
      gameRegistration?.unregister?.();
      downloadRegistration?.unregister?.();
      void setSteamActivity(false, "").catch(() => undefined);
    };
  }, [onGame]);
}
