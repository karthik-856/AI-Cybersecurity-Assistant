import { sessionFetch } from "../../services/sessionFetch";
import { useCapabilities } from "../../services/capabilities";
import { scheduleLoad } from "../../utils/scheduleLoad";
import { useEffect, useState } from "react";
import { Check, Loader2, Mail, ShieldCheck, X } from "lucide-react";
import "./TwoFactorVerification.css";

import { API_BASE_URL } from "../../services/config";

type Status = { enabled: boolean; email: string };
type Action = "enable" | "disable";

async function requestJson(path: string, options: RequestInit = {}) {
  const token = localStorage.getItem("zuka_access_token");
  const response = await sessionFetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok)
    throw new Error(
      data.detail || data.message || `Request failed (${response.status}).`,
    );
  return data;
}

export default function TwoFactorVerification() {
  const capabilities = useCapabilities();
  const [status, setStatus] = useState<Status | null>(null);
  const [action, setAction] = useState<Action | null>(null);
  const [otp, setOtp] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function loadStatus() {
    try {
      const data = await requestJson("/api/auth/2fa/status");
      setStatus(data as Status);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load two-step verification status.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    return scheduleLoad(loadStatus);
  }, []);

  async function begin(nextAction: Action) {
    setError("");
    setMessage("");
    setOtp("");
    setAction(nextAction);
    setSending(true);
    try {
      const data = await requestJson("/api/auth/2fa/request", {
        method: "POST",
        body: JSON.stringify({ action: nextAction }),
      });
      setMessage(
        data.message || "A verification code has been sent to your email.",
      );
    } catch (err) {
      setAction(null);
      setError(
        err instanceof Error
          ? err.message
          : "Unable to send verification code.",
      );
    } finally {
      setSending(false);
    }
  }

  async function verify() {
    if (!action || !/^\d{6}$/.test(otp)) {
      setError("Enter the 6-digit verification code sent to your email.");
      return;
    }
    setError("");
    setMessage("");
    setVerifying(true);
    try {
      const data = await requestJson("/api/auth/2fa/verify", {
        method: "POST",
        body: JSON.stringify({ action, otp }),
      });
      setMessage(data.message || "Two-step verification updated successfully.");
      setAction(null);
      setOtp("");
      await loadStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed.");
    } finally {
      setVerifying(false);
    }
  }

  if (loading)
    return (
      <div className="twofa-panel">
        <Loader2 className="twofa-spin" size={18} />
        <span>Checking two-step verification status…</span>
      </div>
    );

  const enabled = Boolean(status?.enabled);

  return (
    <div className="twofa-panel">
      <div className="twofa-main">
        <div className="twofa-icon">
          <ShieldCheck size={20} />
        </div>
        <div className="twofa-copy">
          <div className="twofa-title-row">
            <strong>Two-step verification</strong>
            <span
              className={`twofa-status ${enabled ? "enabled" : "disabled"}`}
            >
              <span />
              {enabled ? "Enabled" : "Disabled"}
            </span>
          </div>
          <p>
            {enabled
              ? `Login verification codes are sent to ${status?.email || "your registered email"}.`
              : "Add email verification during sign-in."}
          </p>
        </div>
        {!action && (
          <button
            className={enabled ? "twofa-danger-button" : "twofa-primary-button"}
            type="button"
            onClick={() => void begin(enabled ? "disable" : "enable")}
            disabled={sending || !capabilities.two_factor}
          >
            {sending ? (
              <Loader2 className="twofa-spin" size={15} />
            ) : enabled ? (
              <X size={15} />
            ) : (
              <Check size={15} />
            )}
            {sending ? "Sending…" : enabled ? "Disable" : "Enable"}
          </button>
        )}
      </div>

      {action && (
        <div className="twofa-verification-box">
          <div className="twofa-email-note">
            <Mail size={16} />
            <span>
              Enter the 6-digit code sent to <strong>{status?.email}</strong>.
            </span>
          </div>
          <div className="twofa-form-row">
            <input
              aria-label="Two-step verification code"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              value={otp}
              onChange={(e) =>
                setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))
              }
              placeholder="000000"
            />
            <button
              type="button"
              className="twofa-primary-button"
              onClick={() => void verify()}
              disabled={verifying || otp.length !== 6}
            >
              {verifying ? (
                <Loader2 className="twofa-spin" size={15} />
              ) : (
                <Check size={15} />
              )}
              {verifying
                ? "Verifying…"
                : `Verify & ${action === "enable" ? "Enable" : "Disable"}`}
            </button>
            <button
              type="button"
              className="twofa-cancel-button"
              onClick={() => {
                setAction(null);
                setOtp("");
                setError("");
                setMessage("");
              }}
              disabled={verifying}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {!capabilities.two_factor && (
        <p className="twofa-configuration-note">
          Email delivery is not configured. An administrator must finish SMTP
          setup before email codes can be enabled.
        </p>
      )}
      {message && (
        <div className="twofa-success">
          <Check size={15} />
          {message}
        </div>
      )}
      {error && (
        <div className="twofa-error">
          <X size={15} />
          {error}
        </div>
      )}
    </div>
  );
}
