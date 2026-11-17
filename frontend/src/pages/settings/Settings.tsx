import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  Bell,
  Check,
  ChevronRight,
  CircleUserRound,
  Clock3,
  KeyRound,
  Laptop,
  LockKeyhole,
  Palette,
  RefreshCw,
  RotateCcw,
  Save,
  ShieldCheck,
  UserRound,
  Volume2,
  VolumeX,
  X,
} from "lucide-react";
import { formatShortDateTime } from "../../utils/datetime";
import "./Settings.css";
import TwoFactorVerification from "../../components/security/TwoFactorVerification";
import PasswordRequirements from "../../components/auth/PasswordRequirements";
import { evaluatePassword } from "../../utils/password";
import {
  disablePersistentPush,
  ensurePersistentPush,
  testBrowserNotification,
  requestBrowserNotificationPermission,
} from "../../services/push";
import { getPushStatus } from "../../services/api";
import { playAlertSound } from "../../services/alertSound";
import {
  changePassword,
  getActiveSessions,
  getLoginActivity,
  revokeAllOtherSessions,
  revokeSession,
  type AuthSession,
  type LoginActivity,
} from "../../services/auth";

type SectionKey = "profile" | "security" | "notifications" | "appearance";
type Density = "comfortable" | "compact";

interface Preferences {
  density: Density;
  reducedMotion: boolean;
  criticalAlerts: boolean;
  highAlerts: boolean;
  browserNotifications: boolean;
  soundNotifications: boolean;
  notificationPreview: boolean;
  confidenceThreshold: number;
  replayRateSeconds: number;
  treeShapEnabled: boolean;
  timeFormat: "local" | "utc";
  refreshIntervalSeconds: number;
  defaultEscalationPriority: "P1" | "P2";
}

const STORAGE_KEY = "zuka_settings_preferences_v2";
const DEFAULT_PREFERENCES: Preferences = {
  density: "comfortable",
  reducedMotion: false,
  criticalAlerts: true,
  highAlerts: true,
  browserNotifications: false,
  soundNotifications: true,
  notificationPreview: true,
  confidenceThreshold: 85,
  replayRateSeconds: 5,
  treeShapEnabled: true,
  timeFormat: "local",
  refreshIntervalSeconds: 5,
  defaultEscalationPriority: "P1",
};

const sections: Array<{
  key: SectionKey;
  label: string;
  description: string;
  icon: typeof UserRound;
}> = [
  {
    key: "profile",
    label: "Profile & Account",
    description: "Identity and password credentials",
    icon: CircleUserRound,
  },
  {
    key: "security",
    label: "Security & Sessions",
    description: "Active sessions and login audit logs",
    icon: ShieldCheck,
  },
  {
    key: "notifications",
    label: "Alert Notifications",
    description: "Severity thresholds and Web Push",
    icon: Bell,
  },
  {
    key: "appearance",
    label: "Workspace & Display",
    description: "Interface density and motion",
    icon: Palette,
  },
];

function loadPreferences(): Preferences {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw
      ? { ...DEFAULT_PREFERENCES, ...JSON.parse(raw) }
      : DEFAULT_PREFERENCES;
  } catch {
    return DEFAULT_PREFERENCES;
  }
}

function persistSoundPreference(enabled: boolean) {
  try {
    const currentV2 = JSON.parse(
      localStorage.getItem(STORAGE_KEY) || "{}",
    ) as Record<string, unknown>;
    const rawV1 = localStorage.getItem("zuka_settings_preferences");
    const currentV1 = JSON.parse(rawV1 || "{}") as Record<string, unknown>;
    const legacySeed = rawV1
      ? {}
      : { browserNotifications: currentV2.browserNotifications };
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ ...currentV2, soundNotifications: enabled }),
    );
    localStorage.setItem(
      "zuka_settings_preferences",
      JSON.stringify({
        ...legacySeed,
        ...currentV1,
        soundNotifications: enabled,
      }),
    );
    window.dispatchEvent(
      new CustomEvent("zuka_preferences_updated", {
        detail: { soundNotifications: enabled },
      }),
    );
  } catch {
    // The in-memory setting still applies for this page session.
  }
}

function getStoredUser() {
  try {
    const raw = localStorage.getItem("zuka_user");
    if (!raw) return null;
    return JSON.parse(raw) as {
      username?: string;
      email?: string;
      role?: string;
      is_active?: boolean;
    };
  } catch {
    return null;
  }
}

function maskEmail(email: string) {
  const [name, domain] = email.split("@");
  if (!name || !domain) return email;
  if (name.length <= 2) return `${name[0] ?? "*"}***@${domain}`;
  return `${name[0]}${"*".repeat(Math.min(Math.max(name.length - 2, 3), 7))}${name.at(-1)}@${domain}`;
}

function Toggle({
  checked,
  onChange,
  label,
  disabled = false,
}: {
  checked: boolean;
  onChange: (value: boolean) => void;
  label: string;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      className={`settings-toggle ${checked ? "active" : ""}`}
      aria-label={label}
      aria-pressed={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
    >
      <span />
    </button>
  );
}

function SettingRow({
  label,
  description,
  children,
  onClick,
}: {
  label: string;
  description: string;
  children: ReactNode;
  onClick?: () => void;
}) {
  return (
    <div
      className={`settings-row ${onClick ? "settings-row-clickable" : ""}`}
      onClick={onClick}
    >
      <div className="settings-row-copy">
        <strong>{label}</strong>
        <span>{description}</span>
      </div>
      <div
        className="settings-row-control"
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}

function StatusPill({
  children,
  tone = "success",
}: {
  children: ReactNode;
  tone?: "success" | "neutral" | "warning";
}) {
  return (
    <span className={`settings-status-pill ${tone}`}>
      <span />
      {children}
    </span>
  );
}

function ActionRow({
  icon,
  label,
  description,
  action,
  danger = false,
}: {
  icon: ReactNode;
  label: string;
  description: string;
  action: ReactNode;
  danger?: boolean;
}) {
  return (
    <div className={`settings-action-row ${danger ? "danger" : ""}`}>
      <div className="settings-action-icon">{icon}</div>
      <div className="settings-action-copy">
        <strong>{label}</strong>
        <span>{description}</span>
      </div>
      <div>{action}</div>
    </div>
  );
}

export default function Settings() {
  const [activeSection, setActiveSection] = useState<SectionKey>("profile");
  const [preferences, setPreferences] = useState<Preferences>(loadPreferences);
  const [saved, setSaved] = useState(false);
  const [browserPermission, setBrowserPermission] = useState<
    NotificationPermission | "unsupported"
  >(() => ("Notification" in window ? Notification.permission : "unsupported"));
  const [showPasswordPanel, setShowPasswordPanel] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [passwordSuccess, setPasswordSuccess] = useState("");
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [showActivityPanel, setShowActivityPanel] = useState(false);
  const [loginActivity, setLoginActivity] = useState<LoginActivity[]>([]);
  const [activityLoading, setActivityLoading] = useState(false);
  const [activityError, setActivityError] = useState("");
  const [showSessionsPanel, setShowSessionsPanel] = useState(false);
  const [sessions, setSessions] = useState<AuthSession[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [sessionsError, setSessionsError] = useState("");
  const [revokingSessionId, setRevokingSessionId] = useState("");
  const [revokeAllLoading, setRevokeAllLoading] = useState(false);
  const user = useMemo(() => getStoredUser(), []);
  const canReceiveAlerts = ["ADMIN", "SOC_ANALYST"].includes(user?.role ?? "");
  const [notificationBusy, setNotificationBusy] = useState(false);
  const [notificationMessage, setNotificationMessage] = useState("");
  const [backgroundPushConfigured, setBackgroundPushConfigured] = useState<
    boolean | null
  >(null);

  useEffect(() => {
    let cancelled = false;
    void getPushStatus()
      .then((status) => {
        if (!cancelled) setBackgroundPushConfigured(status.configured);
      })
      .catch(() => {
        if (!cancelled)
          setNotificationMessage(
            "Background notification setup could not be checked.",
          );
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    document.documentElement.dataset.zukaDensity = preferences.density;
    document.documentElement.dataset.zukaReducedMotion = String(
      preferences.reducedMotion,
    );
  }, [preferences.density, preferences.reducedMotion]);

  useEffect(() => {
    if (!("Notification" in window)) {
      return;
    }

    let permissionStatus: PermissionStatus | undefined;
    const refreshPermission = () =>
      setBrowserPermission(Notification.permission);
    void navigator.permissions
      ?.query({ name: "notifications" as PermissionName })
      .then((status) => {
        permissionStatus = status;
        status.addEventListener("change", refreshPermission);
      })
      .catch(() => undefined);
    window.addEventListener("focus", refreshPermission);
    return () => {
      window.removeEventListener("focus", refreshPermission);
      permissionStatus?.removeEventListener("change", refreshPermission);
    };
  }, []);

  function update<K extends keyof Preferences>(key: K, value: Preferences[K]) {
    setPreferences((current) => ({ ...current, [key]: value }));
    setSaved(false);
  }

  function updateSoundAlerts(enabled: boolean) {
    update("soundNotifications", enabled);
    persistSoundPreference(enabled);
  }

  function syncPreferencesToStorage(prefs: Preferences) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
    localStorage.setItem(
      "zuka_settings_preferences",
      JSON.stringify({
        notificationsCritical: prefs.criticalAlerts,
        notificationsHigh: prefs.highAlerts,
        browserNotifications: prefs.browserNotifications,
        soundNotifications: prefs.soundNotifications,
        notificationPreview: prefs.notificationPreview,
        confidenceThreshold: prefs.confidenceThreshold,
        replayRateSeconds: prefs.replayRateSeconds,
        treeShapEnabled: prefs.treeShapEnabled,
        timeFormat: prefs.timeFormat,
        refreshIntervalSeconds: prefs.refreshIntervalSeconds,
        defaultEscalationPriority: prefs.defaultEscalationPriority,
      }),
    );
    window.dispatchEvent(
      new CustomEvent("zuka_preferences_updated", { detail: prefs }),
    );
    window.dispatchEvent(new Event("storage"));
  }

  function save() {
    syncPreferencesToStorage(preferences);
    setSaved(true);
    window.setTimeout(() => {
      setSaved(false);
    }, 2800);
  }

  function reset() {
    setPreferences(DEFAULT_PREFERENCES);
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem("zuka_settings_preferences");
    document.documentElement.dataset.zukaDensity = DEFAULT_PREFERENCES.density;
    document.documentElement.dataset.zukaReducedMotion = String(
      DEFAULT_PREFERENCES.reducedMotion,
    );
    window.dispatchEvent(
      new CustomEvent("zuka_preferences_updated", {
        detail: DEFAULT_PREFERENCES,
      }),
    );
    window.dispatchEvent(new Event("storage"));
    setSaved(false);
  }

  async function toggleBrowserNotifications() {
    if (!canReceiveAlerts || notificationBusy) return;
    if (!("Notification" in window)) {
      setNotificationMessage("This browser does not support notifications.");
      return;
    }
    setNotificationBusy(true);
    setNotificationMessage("");
    try {
      if (preferences.browserNotifications) {
        const next = { ...preferences, browserNotifications: false };
        setPreferences(next);
        syncPreferencesToStorage(next);
        await disablePersistentPush();
        setNotificationMessage(
          "Browser notifications disabled for this device.",
        );
      } else {
        const permission =
          Notification.permission === "granted"
            ? "granted"
            : await requestBrowserNotificationPermission();
        setBrowserPermission(permission);
        if (permission !== "granted") {
          setNotificationMessage(
            permission === "denied"
              ? "Notifications are blocked. Allow them in this website’s browser settings, then try again."
              : "Notification permission was not allowed. Use the toggle to try again.",
          );
          return;
        }
        const next = { ...preferences, browserNotifications: true };
        setPreferences(next);
        syncPreferencesToStorage(next);
        const ready =
          backgroundPushConfigured === true
            ? await ensurePersistentPush()
            : false;
        setNotificationMessage(
          ready
            ? "Background notifications enabled for this device. Send a test to verify delivery."
            : "Notifications enabled while this website is open. Background push still needs server setup or device registration.",
        );
      }
      setSaved(false);
    } catch {
      setNotificationMessage(
        "Notification setup failed. Check your browser permission and connection, then try again.",
      );
    } finally {
      setNotificationBusy(false);
    }
  }

  async function testNotification() {
    setNotificationBusy(true);
    try {
      setNotificationMessage(await testBrowserNotification());
    } catch (error) {
      setNotificationMessage(
        error instanceof Error
          ? error.message
          : "The notification test failed.",
      );
    } finally {
      setNotificationBusy(false);
    }
  }

  const browserPermissionDescription =
    browserPermission === "granted"
      ? "Browser permission granted."
      : browserPermission === "denied"
        ? "Notifications are blocked in your browser."
        : browserPermission === "unsupported"
          ? "This browser does not support notifications."
          : "Use the toggle to allow browser notifications.";

  async function openLoginActivity() {
    setShowActivityPanel(true);
    setActivityError("");
    setActivityLoading(true);

    try {
      const records = await getLoginActivity(50);
      setLoginActivity(records);
    } catch (error) {
      setLoginActivity([]);
      setActivityError(
        error instanceof Error
          ? error.message
          : "Unable to load login activity.",
      );
    } finally {
      setActivityLoading(false);
    }
  }

  async function openActiveSessions() {
    setShowSessionsPanel(true);
    setSessionsError("");
    setSessionsLoading(true);

    try {
      const records = await getActiveSessions();
      setSessions(records);
    } catch (error) {
      setSessions([]);
      setSessionsError(
        error instanceof Error
          ? error.message
          : "Unable to load active sessions.",
      );
    } finally {
      setSessionsLoading(false);
    }
  }

  async function refreshActiveSessions() {
    setSessionsError("");
    setSessionsLoading(true);

    try {
      const records = await getActiveSessions();
      setSessions(records);
    } catch (error) {
      setSessionsError(
        error instanceof Error
          ? error.message
          : "Unable to refresh active sessions.",
      );
    } finally {
      setSessionsLoading(false);
    }
  }

  async function handleRevokeSession(session: AuthSession) {
    if (session.is_current || revokingSessionId || revokeAllLoading) return;

    setSessionsError("");
    setRevokingSessionId(session.session_id);

    try {
      await revokeSession(session.session_id);
      setSessions((current) =>
        current.filter((item) => item.session_id !== session.session_id),
      );
    } catch (error) {
      setSessionsError(
        error instanceof Error
          ? error.message
          : "Unable to sign out the selected session.",
      );
    } finally {
      setRevokingSessionId("");
    }
  }

  async function handleRevokeAllSessions() {
    if (revokeAllLoading) {
      return;
    }

    const confirmed = window.confirm(
      "Sign out all other ZUKA sessions? Your current session will remain active.",
    );

    if (!confirmed) return;

    setSessionsError("");
    setRevokeAllLoading(true);

    try {
      const result = await revokeAllOtherSessions();
      const records = await getActiveSessions();
      setSessions(records);

      if (result.revoked_count !== undefined) {
        console.info(
          `ZUKA: signed out ${result.revoked_count} other session(s).`,
        );
      }
    } catch (error) {
      setSessionsError(
        error instanceof Error
          ? error.message
          : "Unable to sign out the other sessions.",
      );
    } finally {
      setRevokeAllLoading(false);
    }
  }

  function formatSessionTime(value?: string | null) {
    if (!value) return "Active now";
    return formatShortDateTime(value);
  }

  function formatSessionDevice(value?: string | null) {
    if (!value) return "Browser / device unavailable";
    if (/Code\//i.test(value) || /Electron\//i.test(value))
      return "VS Code / Electron";
    if (/Edg\//i.test(value)) return "Microsoft Edge";
    if (/OPR\//i.test(value)) return "Opera";
    if (/Firefox\//i.test(value)) return "Mozilla Firefox";
    if (/Chrome\//i.test(value)) return "Google Chrome";
    if (/Safari\//i.test(value)) return "Safari";
    return "Web browser";
  }

  function formatSessionAgent(value?: string | null) {
    if (!value) return "Browser details unavailable";
    if (/Code\//i.test(value) || /Electron\//i.test(value))
      return "Desktop application";
    if (/Windows NT/i.test(value)) return "Windows";
    if (/Macintosh/i.test(value)) return "macOS";
    if (/Linux/i.test(value)) return "Linux";
    return "Browser session";
  }

  function maskSessionId(value: string) {
    if (value.length <= 14) return value;
    return `${value.slice(0, 8)}…${value.slice(-6)}`;
  }

  function formatActivityTime(value: string) {
    if (!value) return "—";
    return formatShortDateTime(value);
  }

  function formatUserAgent(value?: string | null) {
    if (!value) return "Browser / device information unavailable";

    if (/Edg\//i.test(value)) return "Microsoft Edge";
    if (/Chrome\//i.test(value)) return "Google Chrome";
    if (/Firefox\//i.test(value)) return "Mozilla Firefox";
    if (/Safari\//i.test(value) && !/Chrome\//i.test(value)) return "Safari";
    if (/OPR\//i.test(value)) return "Opera";

    return "Web browser";
  }

  const username = user?.username || "Analyst";
  const email = user?.email || "Not available";
  const role = user?.role || "Authenticated user";
  const accountActive = user?.is_active !== false;

  return (
    <main className="settings-page">
      <header className="settings-header">
        <div>
          <span className="settings-eyebrow">ACCOUNT / PREFERENCES</span>
          <h1>Settings</h1>
          <p>
            Manage your ZUKA analyst workspace, notifications, privacy, and
            account security.
          </p>
        </div>
        <div className="settings-account-chip">
          <div className="settings-avatar">
            <UserRound size={17} />
          </div>
          <div>
            <strong>{username}</strong>
            <span>{role}</span>
          </div>
        </div>
      </header>

      <section className="settings-shell">
        <aside className="settings-sidebar">
          <div className="settings-sidebar-title">
            <LockKeyhole size={14} />
            <span>SETTINGS</span>
          </div>
          <nav className="settings-nav" aria-label="Settings sections">
            {sections.map((section) => {
              const Icon = section.icon;
              const active = activeSection === section.key;
              return (
                <button
                  key={section.key}
                  type="button"
                  className={`settings-nav-item ${active ? "active" : ""}`}
                  onClick={() => setActiveSection(section.key)}
                >
                  <Icon size={16} />
                  <span>
                    <strong>{section.label}</strong>
                    <small>{section.description}</small>
                  </span>
                  <ChevronRight size={14} />
                </button>
              );
            })}
          </nav>
          <div className="settings-sidebar-note">
            <ShieldCheck size={15} />
            <span>Enterprise SOC Security Controls</span>
          </div>
        </aside>

        <section className="settings-content">
          {/* 1. PROFILE & ACCOUNT */}
          {activeSection === "profile" && (
            <div className="settings-section">
              <SectionHeader
                eyebrow="ANALYST CREDENTIALS"
                title="Profile & Account"
                description="Manage your analyst identity and update account password."
              />
              <div className="settings-profile-card">
                <div className="settings-profile-avatar">
                  <UserRound size={28} />
                </div>
                <div className="settings-profile-main">
                  <div className="settings-profile-name">{username}</div>
                  <div className="settings-profile-email">
                    {maskEmail(email)}
                  </div>
                </div>
                <StatusPill tone={accountActive ? "success" : "warning"}>
                  {accountActive ? "Account Active" : "Account Inactive"}
                </StatusPill>
              </div>

              <div className="settings-card">
                <SettingRow
                  label="Username"
                  description="Analyst account identifier."
                >
                  <span className="settings-value">{username}</span>
                </SettingRow>
                <SettingRow
                  label="Email address"
                  description="Registered email for system notifications."
                >
                  <span className="settings-value">{maskEmail(email)}</span>
                </SettingRow>
                <SettingRow
                  label="Role authorization"
                  description="Access permissions assigned in PostgreSQL RBAC."
                >
                  <span className="settings-value">{role}</span>
                </SettingRow>
                <SettingRow
                  label="Account state"
                  description="Authentication lifecycle status."
                >
                  <StatusPill tone={accountActive ? "success" : "warning"}>
                    {accountActive ? "Active" : "Inactive"}
                  </StatusPill>
                </SettingRow>
              </div>

              <div className="settings-card settings-actions-card">
                <ActionRow
                  icon={<KeyRound size={17} />}
                  label="Change account password"
                  description="Update your password with cryptographic hashing."
                  action={
                    <button
                      className="settings-secondary-button"
                      onClick={() => setShowPasswordPanel(true)}
                    >
                      Change password
                    </button>
                  }
                />
              </div>
            </div>
          )}

          {/* 2. SECURITY & SESSIONS */}
          {activeSection === "security" && (
            <div className="settings-section">
              <SectionHeader
                eyebrow="AUTHENTICATION CONTROLS"
                title="Security & Sessions"
                description="Enforce two-factor verification, audit login history, and manage active sessions."
              />

              <div className="settings-card">
                <TwoFactorVerification />
              </div>

              <div className="settings-card settings-actions-card">
                <ActionRow
                  icon={<LockKeyhole size={17} />}
                  label="Active authenticated sessions"
                  description="Inspect current browser and device sessions or revoke untrusted logins."
                  action={
                    <button
                      className="settings-secondary-button"
                      onClick={openActiveSessions}
                    >
                      Manage sessions
                    </button>
                  }
                />
                <ActionRow
                  icon={<Clock3 size={17} />}
                  label="Login audit history"
                  description="Review authentication access logs and IP addresses."
                  action={
                    <button
                      className="settings-secondary-button"
                      onClick={openLoginActivity}
                    >
                      View activity
                    </button>
                  }
                />
              </div>
            </div>
          )}

          {/* 3. ALERT NOTIFICATIONS */}
          {activeSection === "notifications" && (
            <div className="settings-section">
              <SectionHeader
                eyebrow="DETECTION TELEMETRY"
                title="Alert Notifications"
                description="Configure real-time alert triggers, browser Web Push, and audio signals."
              />

              <p role="status" aria-live="polite">
                {notificationMessage ||
                  (!canReceiveAlerts
                    ? "Detailed security notifications are available to administrators and SOC analysts."
                    : backgroundPushConfigured === false
                      ? "Background push is not configured on the server. Device notifications can still work while this website is open."
                      : backgroundPushConfigured === true
                        ? "The server supports background push. Enable this device and send a test."
                        : "Checking background notification setup...")}
              </p>

              <div className="settings-card">
                <SettingRow
                  label="Critical severity alerts"
                  description="Notify immediately for CRITICAL machine learning detections."
                  onClick={() =>
                    update("criticalAlerts", !preferences.criticalAlerts)
                  }
                >
                  <Toggle
                    checked={preferences.criticalAlerts}
                    onChange={(v) => update("criticalAlerts", v)}
                    label="Critical alerts"
                  />
                </SettingRow>

                <SettingRow
                  label="High severity alerts"
                  description="Notify for HIGH severity attack classifications."
                  onClick={() => update("highAlerts", !preferences.highAlerts)}
                >
                  <Toggle
                    checked={preferences.highAlerts}
                    onChange={(v) => update("highAlerts", v)}
                    label="High severity alerts"
                  />
                </SettingRow>

                <SettingRow
                  label="Browser notifications"
                  description={`Receive Web Push banners for active detections. ${browserPermissionDescription}`}
                  onClick={toggleBrowserNotifications}
                >
                  <div className="settings-control-stack">
                    <Toggle
                      checked={
                        preferences.browserNotifications &&
                        browserPermission === "granted"
                      }
                      onChange={toggleBrowserNotifications}
                      label="Browser notifications"
                      disabled={
                        notificationBusy ||
                        !canReceiveAlerts ||
                        browserPermission === "unsupported"
                      }
                    />
                    <button
                      type="button"
                      className="settings-secondary-button"
                      disabled={
                        notificationBusy ||
                        !canReceiveAlerts ||
                        !preferences.browserNotifications ||
                        browserPermission !== "granted"
                      }
                      onClick={() => void testNotification()}
                    >
                      Send test notification
                    </button>
                  </div>
                </SettingRow>

                <SettingRow
                  label="Sound alerts"
                  description="Play a sound for critical and high-severity alerts."
                  onClick={() =>
                    updateSoundAlerts(!preferences.soundNotifications)
                  }
                >
                  <div className="settings-inline-control">
                    <button
                      type="button"
                      className="settings-icon-toggle-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        updateSoundAlerts(!preferences.soundNotifications);
                      }}
                      aria-label="Toggle sound alerts"
                    >
                      {preferences.soundNotifications ? (
                        <Volume2 size={16} />
                      ) : (
                        <VolumeX size={16} />
                      )}
                    </button>
                    <Toggle
                      checked={preferences.soundNotifications}
                      onChange={updateSoundAlerts}
                      label="Sound notifications"
                    />
                    <button
                      type="button"
                      className="settings-secondary-button"
                      onClick={() => {
                        void playAlertSound().then((played) =>
                          setNotificationMessage(
                            played
                              ? "Test sound started. Check your device volume."
                              : "Sound could not start. Check browser and device audio settings.",
                          ),
                        );
                      }}
                    >
                      Test sound
                    </button>
                  </div>
                </SettingRow>

                <SettingRow
                  label="Attack preview in notifications"
                  description="Display predicted attack class and confidence score in alerts."
                  onClick={() =>
                    update(
                      "notificationPreview",
                      !preferences.notificationPreview,
                    )
                  }
                >
                  <Toggle
                    checked={preferences.notificationPreview}
                    onChange={(v) => update("notificationPreview", v)}
                    label="Notification preview"
                  />
                </SettingRow>
              </div>
            </div>
          )}

          {/* 4. WORKSPACE & DISPLAY */}
          {activeSection === "appearance" && (
            <div className="settings-section">
              <SectionHeader
                eyebrow="WORKSPACE DISPLAY"
                title="Workspace & Display"
                description="Adjust density and animation settings for your monitor."
              />

              <div className="settings-card">
                <SettingRow
                  label="Interface layout density"
                  description="Comfortable provides spacious viewing; compact optimizes data density."
                >
                  <div className="settings-segmented">
                    <button
                      type="button"
                      className={
                        preferences.density === "comfortable" ? "selected" : ""
                      }
                      onClick={() => update("density", "comfortable")}
                    >
                      Comfortable
                    </button>
                    <button
                      type="button"
                      className={
                        preferences.density === "compact" ? "selected" : ""
                      }
                      onClick={() => update("density", "compact")}
                    >
                      Compact
                    </button>
                  </div>
                </SettingRow>

                <SettingRow
                  label="Reduced motion"
                  description="Disable non-essential dashboard animations."
                  onClick={() =>
                    update("reducedMotion", !preferences.reducedMotion)
                  }
                >
                  <Toggle
                    checked={preferences.reducedMotion}
                    onChange={(v) => update("reducedMotion", v)}
                    label="Reduced motion"
                  />
                </SettingRow>
              </div>
            </div>
          )}
        </section>
      </section>

      <footer className="settings-footer">
        <div />
        <div className="settings-actions">
          <button
            type="button"
            className="settings-reset-button"
            onClick={reset}
          >
            <RotateCcw size={14} /> Reset Defaults
          </button>
          <button type="button" className="settings-save-button" onClick={save}>
            {saved ? <Check size={14} /> : <Save size={14} />}
            {saved ? "Saved" : "Save Changes"}
          </button>
        </div>
      </footer>

      {showActivityPanel && (
        <div
          className="settings-modal-backdrop"
          role="presentation"
          onClick={() => !activityLoading && setShowActivityPanel(false)}
        >
          <div
            className="settings-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="activity-dialog-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="settings-modal-header">
              <div>
                <span>ACCOUNT SECURITY</span>
                <h2 id="activity-dialog-title">Login activity</h2>
                <p>
                  Recent successful and failed sign-in attempts for this ZUKA
                  account.
                </p>
              </div>
              <button
                className="settings-modal-close"
                onClick={() => setShowActivityPanel(false)}
                aria-label="Close"
                disabled={activityLoading}
              >
                <X size={18} />
              </button>
            </div>

            {activityLoading && (
              <div className="settings-activity-state">
                <Clock3 size={22} />
                <strong>Loading activity</strong>
                <span>Retrieving recent authentication events...</span>
              </div>
            )}

            {!activityLoading && activityError && (
              <div className="settings-form-error" role="alert">
                {activityError}
              </div>
            )}

            {!activityLoading &&
              !activityError &&
              loginActivity.length === 0 && (
                <div className="settings-activity-state">
                  <Clock3 size={22} />
                  <strong>No login activity found</strong>
                  <span>
                    There are no authentication records available for this
                    account yet.
                  </span>
                </div>
              )}

            {!activityLoading && !activityError && loginActivity.length > 0 && (
              <div className="settings-activity-list">
                {loginActivity.map((record) => (
                  <div
                    className={`settings-activity-item ${
                      record.success ? "success" : "failed"
                    }`}
                    key={record.id}
                  >
                    <div className="settings-activity-status">
                      {record.success ? <Check size={16} /> : <X size={16} />}
                    </div>

                    <div className="settings-activity-copy">
                      <strong>
                        {record.success
                          ? "Successful sign-in"
                          : "Failed sign-in"}
                      </strong>
                      <span>{formatActivityTime(record.login_at)}</span>
                      <small>
                        {record.ip_address || "IP address unavailable"} ·{" "}
                        {formatUserAgent(record.user_agent)}
                      </small>
                    </div>

                    <span
                      className={`settings-activity-badge ${
                        record.success ? "success" : "failed"
                      }`}
                    >
                      {record.success ? "SUCCESS" : "FAILED"}
                    </span>
                  </div>
                ))}
              </div>
            )}

            <div className="settings-password-actions">
              <button
                type="button"
                className="settings-secondary-button"
                onClick={() => setShowActivityPanel(false)}
              >
                Close
              </button>
              <button
                type="button"
                className="settings-save-button"
                onClick={openLoginActivity}
                disabled={activityLoading}
              >
                Refresh activity
              </button>
            </div>
          </div>
        </div>
      )}

      {showSessionsPanel && (
        <div
          className="settings-modal-backdrop"
          role="presentation"
          onClick={() =>
            !sessionsLoading && !revokeAllLoading && setShowSessionsPanel(false)
          }
        >
          <div
            className="settings-modal settings-sessions-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="sessions-dialog-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="settings-modal-header">
              <div>
                <span>ACCOUNT SECURITY</span>
                <h2 id="sessions-dialog-title">Active sessions</h2>
                <p>
                  Review the browsers and devices currently authenticated to
                  your ZUKA account.
                </p>
              </div>
              <button
                className="settings-modal-close"
                onClick={() => setShowSessionsPanel(false)}
                aria-label="Close"
                disabled={sessionsLoading || revokeAllLoading}
              >
                <X size={18} />
              </button>
            </div>

            {sessionsLoading && (
              <div className="settings-activity-state">
                <RefreshCw size={22} />
                <strong>Loading active sessions</strong>
                <span>Retrieving authenticated browsers and devices...</span>
              </div>
            )}

            {!sessionsLoading && sessionsError && (
              <div className="settings-form-error" role="alert">
                {sessionsError}
              </div>
            )}

            {!sessionsLoading && !sessionsError && sessions.length === 0 && (
              <div className="settings-activity-state">
                <Laptop size={22} />
                <strong>No active sessions found</strong>
                <span>
                  No unrevoked and unexpired authentication sessions are
                  available.
                </span>
              </div>
            )}

            {!sessionsLoading && !sessionsError && sessions.length > 0 && (
              <div className="settings-sessions-list">
                {sessions.map((session) => (
                  <div
                    className={`settings-session-item ${
                      session.is_current ? "current" : ""
                    }`}
                    key={session.session_id}
                  >
                    <div className="settings-session-icon">
                      <Laptop size={18} />
                    </div>

                    <div className="settings-session-copy">
                      <div className="settings-session-title">
                        <strong>
                          {formatSessionDevice(session.user_agent)}
                        </strong>
                        {session.is_current && (
                          <span className="settings-session-current">
                            CURRENT SESSION
                          </span>
                        )}
                      </div>

                      <span>
                        {formatSessionAgent(session.user_agent)} ·{" "}
                        {session.ip_address || "IP unavailable"}
                      </span>

                      <small>
                        Last active {formatSessionTime(session.last_seen_at)}
                      </small>

                      <small>
                        Signed in {formatSessionTime(session.created_at)} ·
                        Expires {formatSessionTime(session.expires_at)}
                      </small>

                      <small className="settings-session-id">
                        Session {maskSessionId(session.session_id)}
                      </small>
                    </div>

                    {!session.is_current && (
                      <button
                        type="button"
                        className="settings-session-revoke-button"
                        onClick={() => handleRevokeSession(session)}
                        disabled={
                          revokingSessionId === session.session_id ||
                          Boolean(revokingSessionId) ||
                          revokeAllLoading
                        }
                      >
                        {revokingSessionId === session.session_id
                          ? "Signing out…"
                          : "Sign out"}
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}

            <div className="settings-session-footer">
              <span>
                {sessions.filter((session) => !session.is_current).length} other{" "}
                {sessions.filter((session) => !session.is_current).length === 1
                  ? "session"
                  : "sessions"}{" "}
                can be signed out.
              </span>

              <div className="settings-password-actions">
                <button
                  type="button"
                  className="settings-secondary-button"
                  onClick={() => setShowSessionsPanel(false)}
                  disabled={sessionsLoading || revokeAllLoading}
                >
                  Close
                </button>

                <button
                  type="button"
                  className="settings-save-button"
                  onClick={refreshActiveSessions}
                  disabled={sessionsLoading || revokeAllLoading}
                >
                  <RefreshCw size={14} />
                  Refresh
                </button>

                <button
                  type="button"
                  className="settings-danger-button"
                  onClick={handleRevokeAllSessions}
                  disabled={revokeAllLoading}
                >
                  {revokeAllLoading ? "Signing out…" : "Sign out all others"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showPasswordPanel && (
        <div
          className="settings-modal-backdrop"
          role="presentation"
          onClick={() => !passwordLoading && setShowPasswordPanel(false)}
        >
          <div
            className="settings-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="password-dialog-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="settings-modal-header">
              <div>
                <span>ACCOUNT SECURITY</span>
                <h2 id="password-dialog-title">Change password</h2>
                <p>Verify your current password before setting a new one.</p>
              </div>
              <button
                className="settings-modal-close"
                onClick={() => setShowPasswordPanel(false)}
                aria-label="Close"
                disabled={passwordLoading}
              >
                <X size={18} />
              </button>
            </div>

            <form
              className="settings-password-form"
              onSubmit={async (event) => {
                event.preventDefault();
                setPasswordError("");
                setPasswordSuccess("");

                if (!currentPassword || !newPassword || !confirmPassword) {
                  setPasswordError("Please complete all password fields.");
                  return;
                }

                const pwdCheck = evaluatePassword(newPassword);
                if (!pwdCheck.isValid) {
                  setPasswordError(
                    pwdCheck.firstError ||
                      "New password must meet enterprise complexity conditions (e.g. first letter capital, minimum 8 characters, number, symbol).",
                  );
                  return;
                }

                if (newPassword !== confirmPassword) {
                  setPasswordError(
                    "New password and confirmation do not match.",
                  );
                  return;
                }

                if (currentPassword === newPassword) {
                  setPasswordError(
                    "New password must be different from your current password.",
                  );
                  return;
                }

                setPasswordLoading(true);
                try {
                  const result = await changePassword({
                    current_password: currentPassword,
                    new_password: newPassword,
                    confirm_password: confirmPassword,
                  });
                  setPasswordSuccess(
                    result.message || "Password changed successfully.",
                  );
                  setCurrentPassword("");
                  setNewPassword("");
                  setConfirmPassword("");
                } catch (error) {
                  setPasswordError(
                    error instanceof Error
                      ? error.message
                      : "Unable to change password.",
                  );
                } finally {
                  setPasswordLoading(false);
                }
              }}
            >
              <label className="settings-password-field">
                <span>Current password</span>
                <input
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  autoComplete="current-password"
                  disabled={passwordLoading}
                />
              </label>

              <label className="settings-password-field">
                <span>New password</span>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  autoComplete="new-password"
                  minLength={8}
                  disabled={passwordLoading}
                  placeholder="e.g. SecOps@2026!"
                />
                <PasswordRequirements password={newPassword} />
              </label>

              <label className="settings-password-field">
                <span>Confirm new password</span>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  autoComplete="new-password"
                  minLength={8}
                  disabled={passwordLoading}
                />
              </label>

              {passwordError && (
                <div className="settings-form-error" role="alert">
                  {passwordError}
                </div>
              )}

              {passwordSuccess && (
                <div className="settings-form-success" role="status">
                  {passwordSuccess}
                </div>
              )}

              <div className="settings-password-actions">
                <button
                  type="button"
                  className="settings-secondary-button"
                  onClick={() => setShowPasswordPanel(false)}
                  disabled={passwordLoading}
                >
                  Close
                </button>
                <button
                  type="submit"
                  className="settings-save-button"
                  disabled={passwordLoading}
                >
                  {passwordLoading
                    ? "Changing…"
                    : passwordSuccess
                      ? "Password Changed"
                      : "Change Password"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </main>
  );
}

function SectionHeader({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <header className="settings-section-header">
      <span>{eyebrow}</span>
      <h2>{title}</h2>
      <p>{description}</p>
    </header>
  );
}
