import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlertTriangle,
  Bell,
  ChevronRight,
  CircleAlert,
  ShieldAlert,
  X,
} from "lucide-react";
import { getAlerts, type Alert } from "../../services/api";
import {
  disablePersistentPush,
  ensurePersistentPush,
  showForegroundAlert,
} from "../../services/push";
import { playAlertSound, prepareAlertAudio } from "../../services/alertSound";
import "./NotificationCenter.css";

const POLL_MS = 5000;
const MAX_ITEMS = 20;
const SEEN_KEY = "zuka_notification_seen_ids";
const DISMISSED_KEY = "zuka_notification_dismissed_ids";
const PREF_KEY = "zuka_settings_preferences";
const SWIPE_DISTANCE = 80;

type Preferences = {
  notificationsCritical?: boolean;
  notificationsHigh?: boolean;
  browserNotifications?: boolean;
  soundNotifications?: boolean;
  notificationPreview?: boolean;
};

function readPreferences(): Preferences {
  try {
    const rawV1 = localStorage.getItem(PREF_KEY);
    const rawV2 = localStorage.getItem("zuka_settings_preferences_v2");
    const v2 = rawV2 ? JSON.parse(rawV2) : {};
    const v1 = rawV1 ? JSON.parse(rawV1) : {};
    return {
      notificationsCritical:
        v2.criticalAlerts ?? v1.notificationsCritical ?? true,
      notificationsHigh: v2.highAlerts ?? v1.notificationsHigh ?? true,
      browserNotifications:
        v2.browserNotifications ?? v1.browserNotifications ?? false,
      soundNotifications:
        v2.soundNotifications ?? v1.soundNotifications ?? true,
      notificationPreview:
        v2.notificationPreview ?? v1.notificationPreview ?? true,
    };
  } catch {
    return {};
  }
}

function readIdSet(key: string): Set<string> {
  try {
    const value = JSON.parse(localStorage.getItem(key) || "[]");
    return Array.isArray(value) ? new Set(value.map(String)) : new Set();
  } catch {
    return new Set();
  }
}

function saveIdSet(key: string, ids: Set<string>) {
  localStorage.setItem(key, JSON.stringify(Array.from(ids).slice(-500)));
}

function parseAlertDate(value: string): Date {
  const raw = String(value || "").trim();

  if (!raw) return new Date(NaN);

  // Backend may return a UTC-naive ISO datetime. Treat it as UTC.
  if (!raw.endsWith("Z") && !/[+-]\d{2}:?\d{2}$/.test(raw)) {
    return new Date(`${raw}Z`);
  }

  return new Date(raw);
}

function formatExactTime(value: string): string {
  const date = parseAlertDate(value);

  if (!Number.isFinite(date.getTime())) {
    return "Time unavailable";
  }

  return new Intl.DateTimeFormat("en-IN", {
    timeZone: "Asia/Kolkata",
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
    timeZoneName: "short",
  }).format(date);
}

function playConfiguredAlertSound() {
  const preferences = readPreferences();
  if (preferences.soundNotifications === false) return;
  void playAlertSound();
}

export default function NotificationCenter() {
  const navigate = useNavigate();

  const [open, setOpen] = useState(false);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [error, setError] = useState("");
  const [unreadIds, setUnreadIds] = useState<Set<string>>(new Set());
  const [dragX, setDragX] = useState<Record<string, number>>({});

  const seenRef = useRef<Set<string>>(readIdSet(SEEN_KEY));
  const dismissedRef = useRef<Set<string>>(readIdSet(DISMISSED_KEY));
  const knownIdsRef = useRef<Set<string>>(new Set());
  const initializedRef = useRef(false);
  const pointerStartRef = useRef<Record<string, number>>({});
  const swipeTriggeredRef = useRef<Set<string>>(new Set());
  const suppressClickRef = useRef(false);

  const load = useCallback(async () => {
    try {
      const response = await getAlerts({
        limit: 100,
        offset: 0,
      });

      const relevant = response.alerts
        .filter(
          (alert: Alert) =>
            alert.severity === "CRITICAL" || alert.severity === "HIGH",
        )
        .sort(
          (a: Alert, b: Alert) =>
            parseAlertDate(b.detected_at).getTime() -
            parseAlertDate(a.detected_at).getTime(),
        );

      const visible = relevant.filter(
        (alert) => !dismissedRef.current.has(String(alert.alert_id)),
      );

      setAlerts(visible.slice(0, MAX_ITEMS));
      setError("");

      const preferences = readPreferences();

      // First successful poll establishes the current queue as history.
      // Only alerts appearing after this baseline become notifications.
      if (!initializedRef.current) {
        relevant.forEach((alert) => {
          const id = String(alert.alert_id);
          knownIdsRef.current.add(id);
          seenRef.current.add(id);
        });

        saveIdSet(SEEN_KEY, seenRef.current);
        setUnreadIds(new Set());
        initializedRef.current = true;
        return;
      }

      const newIds: string[] = [];

      for (const alert of relevant) {
        const id = String(alert.alert_id);

        if (knownIdsRef.current.has(id)) continue;

        knownIdsRef.current.add(id);
        newIds.push(id);

        const enabled =
          alert.severity === "CRITICAL"
            ? preferences.notificationsCritical !== false
            : preferences.notificationsHigh !== false;

        if (enabled) {
          playConfiguredAlertSound();
          void showForegroundAlert(alert).catch(() => undefined);
        }
      }

      if (newIds.length > 0) {
        setUnreadIds((current) => {
          const next = new Set(current);
          newIds.forEach((id) => next.add(id));
          return next;
        });
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load security notifications.",
      );
    }
  }, []);

  useEffect(() => {
    prepareAlertAudio();
  }, []);

  useEffect(() => {
    const syncPushPermission = () => {
      const preferences = readPreferences();
      if (
        preferences.browserNotifications &&
        "Notification" in window &&
        Notification.permission === "granted"
      ) {
        void ensurePersistentPush();
      } else {
        void disablePersistentPush();
      }
    };

    syncPushPermission();
    window.addEventListener("zuka_preferences_updated", syncPushPermission);
    window.addEventListener("focus", syncPushPermission);
    return () => {
      window.removeEventListener(
        "zuka_preferences_updated",
        syncPushPermission,
      );
      window.removeEventListener("focus", syncPushPermission);
    };
  }, []);

  useEffect(() => {
    void load();

    const timer = window.setInterval(() => {
      void load();
    }, POLL_MS);

    return () => window.clearInterval(timer);
  }, [load]);

  const unreadCount = unreadIds.size;

  const criticalCount = useMemo(
    () => alerts.filter((alert) => alert.severity === "CRITICAL").length,
    [alerts],
  );

  function markAllRead() {
    alerts.forEach((alert) => {
      const id = String(alert.alert_id);
      seenRef.current.add(id);
    });

    saveIdSet(SEEN_KEY, seenRef.current);

    setUnreadIds((current) => {
      const next = new Set(current);
      alerts.forEach((alert) => {
        next.delete(String(alert.alert_id));
      });
      return next;
    });
  }

  const dismissAlert = useCallback((alertId: string) => {
    dismissedRef.current.add(alertId);
    seenRef.current.add(alertId);

    saveIdSet(DISMISSED_KEY, dismissedRef.current);
    saveIdSet(SEEN_KEY, seenRef.current);

    setUnreadIds((current) => {
      const next = new Set(current);
      next.delete(alertId);
      return next;
    });

    setAlerts((current) =>
      current.filter((alert) => String(alert.alert_id) !== alertId),
    );

    setDragX((current) => {
      const next = { ...current };
      delete next[alertId];
      return next;
    });
  }, []);

  function clearAll() {
    alerts.forEach((alert) => {
      const id = String(alert.alert_id);
      dismissedRef.current.add(id);
      seenRef.current.add(id);
    });

    saveIdSet(DISMISSED_KEY, dismissedRef.current);
    saveIdSet(SEEN_KEY, seenRef.current);

    setUnreadIds(new Set());
    setAlerts([]);
    setDragX({});
  }

  function openAlert(alert: Alert) {
    const id = String(alert.alert_id);

    seenRef.current.add(id);
    saveIdSet(SEEN_KEY, seenRef.current);

    setUnreadIds((current) => {
      const next = new Set(current);
      next.delete(id);
      return next;
    });

    setOpen(false);
    navigate(`/alerts?alert=${encodeURIComponent(alert.alert_id)}`);
  }

  function handlePointerDown(
    alertId: string,
    event: React.PointerEvent<HTMLButtonElement>,
  ) {
    pointerStartRef.current[alertId] = event.clientX;
    swipeTriggeredRef.current.delete(alertId);
    event.currentTarget.setPointerCapture?.(event.pointerId);
  }

  function handlePointerMove(
    alertId: string,
    event: React.PointerEvent<HTMLButtonElement>,
  ) {
    const start = pointerStartRef.current[alertId];
    if (start === undefined) return;

    const delta = event.clientX - start;

    if (delta >= 0) {
      setDragX((current) => ({ ...current, [alertId]: 0 }));
      return;
    }

    const offset = Math.max(delta, -180);

    setDragX((current) => ({
      ...current,
      [alertId]: offset,
    }));

    if (Math.abs(delta) >= SWIPE_DISTANCE) {
      swipeTriggeredRef.current.add(alertId);
    }
  }

  function handlePointerUp(
    alertId: string,
    event: React.PointerEvent<HTMLButtonElement>,
  ) {
    const start = pointerStartRef.current[alertId];
    const delta = start === undefined ? 0 : event.clientX - start;

    delete pointerStartRef.current[alertId];

    if (swipeTriggeredRef.current.has(alertId) || delta <= -SWIPE_DISTANCE) {
      swipeTriggeredRef.current.delete(alertId);
      suppressClickRef.current = true;
      dismissAlert(alertId);
      return;
    }

    swipeTriggeredRef.current.delete(alertId);

    setDragX((current) => ({
      ...current,
      [alertId]: 0,
    }));
  }

  function handlePointerCancel(alertId: string) {
    delete pointerStartRef.current[alertId];
    swipeTriggeredRef.current.delete(alertId);

    setDragX((current) => ({
      ...current,
      [alertId]: 0,
    }));
  }

  return (
    <div className="zuka-notification-center">
      <button
        type="button"
        className={`zuka-notification-trigger ${
          criticalCount > 0 ? "has-critical" : ""
        }`}
        aria-label="Open security notifications"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <Bell size={18} />

        {unreadCount > 0 && (
          <span className="zuka-notification-badge">
            {Math.min(unreadCount, 99)}
          </span>
        )}
      </button>

      {open && (
        <>
          <button
            type="button"
            className="zuka-notification-backdrop"
            aria-label="Close notifications"
            onClick={() => setOpen(false)}
          />

          <section
            className="zuka-notification-panel"
            aria-label="Security notifications"
          >
            <header className="zuka-notification-panel-header">
              <div>
                <span className="zuka-notification-kicker">
                  SOC / NOTIFICATIONS
                </span>
                <h2>Security Notifications</h2>
                <p>
                  {alerts.length} critical/high alert
                  {alerts.length === 1 ? "" : "s"} in the current queue.
                </p>
              </div>

              <button
                type="button"
                className="zuka-notification-close"
                onClick={() => setOpen(false)}
                aria-label="Close notifications"
              >
                <X size={16} />
              </button>
            </header>

            <div className="zuka-notification-toolbar">
              <span>
                {unreadCount > 0 ? `${unreadCount} unread` : "All viewed"}
              </span>

              <button
                type="button"
                onClick={markAllRead}
                disabled={unreadCount === 0}
              >
                Mark all read
              </button>
            </div>

            {error && (
              <div className="zuka-notification-error">
                <CircleAlert size={15} />
                {error}
              </div>
            )}

            <div className="zuka-notification-list">
              {alerts.length === 0 && !error && (
                <div className="zuka-notification-empty">
                  <ShieldAlert size={28} />
                  <strong>No critical or high alerts</strong>
                  <span>
                    Swipe a notification left or use Clear All. New security
                    alerts will appear automatically.
                  </span>
                </div>
              )}

              {alerts.map((alert) => {
                const id = String(alert.alert_id);
                const offset = dragX[id] || 0;
                const exactTime = formatExactTime(alert.detected_at);
                const isUnread = unreadIds.has(id);

                return (
                  <button
                    type="button"
                    key={id}
                    className={`zuka-notification-item ${alert.severity.toLowerCase()} ${isUnread ? "unread" : ""}`}
                    style={{
                      transform: `translateX(${offset}px)`,
                    }}
                    onPointerDown={(event) => handlePointerDown(id, event)}
                    onPointerMove={(event) => handlePointerMove(id, event)}
                    onPointerUp={(event) => handlePointerUp(id, event)}
                    onPointerCancel={() => handlePointerCancel(id)}
                    onClick={() => {
                      if (suppressClickRef.current) {
                        suppressClickRef.current = false;
                        return;
                      }

                      openAlert(alert);
                    }}
                  >
                    <span className="zuka-notification-severity-icon">
                      <AlertTriangle size={17} />
                    </span>

                    <span className="zuka-notification-item-copy">
                      <span className="zuka-notification-item-top">
                        <strong>{alert.severity}</strong>
                        <time dateTime={alert.detected_at} title={exactTime}>
                          {exactTime}
                        </time>
                      </span>

                      <b>{alert.predicted_class}</b>

                      <span className="zuka-notification-description">
                        {alert.description ||
                          "Security threat detected by the ZUKA detection pipeline."}
                      </span>

                      <small>
                        Confidence {(alert.confidence * 100).toFixed(2)}%{" · "}
                        {alert.alert_id}
                      </small>
                    </span>

                    <ChevronRight size={16} />
                  </button>
                );
              })}
            </div>

            <footer className="zuka-notification-panel-footer">
              <button
                type="button"
                className="zuka-notification-open-alerts"
                onClick={() => {
                  setOpen(false);
                  navigate("/alerts");
                }}
              >
                Open Alert Center
              </button>

              <button
                type="button"
                className="zuka-notification-clear"
                onClick={clearAll}
                disabled={alerts.length === 0}
              >
                Clear All
              </button>
            </footer>
          </section>
        </>
      )}
    </div>
  );
}
