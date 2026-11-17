import { Link } from "react-router-dom";
import { useCapabilities } from "../../services/capabilities";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import {
  CheckCircle2,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  Shield,
  User,
} from "lucide-react";
import { register, resendVerification, verifyEmail } from "../../services/auth";
import OtpInput from "../../components/auth/OtpInput";
import PasswordRequirements from "../../components/auth/PasswordRequirements";
import { evaluatePassword } from "../../utils/password";
import "./Register.css";

type RegisterView = "form" | "verify";

function Register() {
  const capabilities = useCapabilities();
  const navigate = useNavigate();

  const [view, setView] = useState<RegisterView>("form");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const role = "VIEWER" as const;
  const [otp, setOtp] = useState("");

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);
  const [resendSeconds, setResendSeconds] = useState(0);

  useEffect(() => {
    if (resendSeconds <= 0) return;
    const timer = window.setInterval(
      () => setResendSeconds((value) => Math.max(0, value - 1)),
      1000,
    );
    return () => window.clearInterval(timer);
  }, [resendSeconds]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading) return;

    setError("");
    setSuccess("");

    const pwdCheck = evaluatePassword(password);
    if (!pwdCheck.isValid) {
      setError(
        pwdCheck.firstError ||
          "Password must meet enterprise complexity conditions (e.g. first letter capital, minimum 8 characters, number, symbol).",
      );
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      const result = await register({
        username: username.trim(),
        email: email.trim(),
        password,
        role,
      });

      setSuccess(
        result.message ||
          "Account created. Check your email for the 6-digit verification code.",
      );
      setView("verify");
      setOtp("");
      setResendSeconds(60);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to create account.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleVerify(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading) return;

    setError("");
    setSuccess("");

    if (!/^\d{6}$/.test(otp)) {
      setError("Enter the 6-digit verification code sent to your email.");
      return;
    }

    setLoading(true);
    try {
      const result = await verifyEmail({
        email: email.trim(),
        otp,
      });

      navigate("/login", {
        replace: true,
        state: {
          email: email.trim(),
          message:
            result.message ||
            "Email verified successfully. You can now sign in.",
        },
      });
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Email verification failed.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleResend() {
    if (loading || resendSeconds > 0) return;

    setError("");
    setSuccess("");
    setLoading(true);

    try {
      const result = await resendVerification({ email: email.trim() });
      setSuccess(result.message || "A new verification code has been sent.");
      setResendSeconds(60);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to resend verification code.",
      );
    } finally {
      setLoading(false);
    }
  }

  if (capabilities.loading)
    return (
      <main className="register-page">
        <section className="register-card">
          <p role="status">Checking account availability...</p>
        </section>
      </main>
    );

  if (!capabilities.registration)
    return (
      <main className="register-page">
        <section className="register-card">
          <h1>Create your account</h1>
          <p>
            Email sign-up is temporarily unavailable. Please try again once
            email delivery is restored.
          </p>
          <Link to="/login">Back to sign in</Link>
        </section>
      </main>
    );

  return (
    <main className="register-page">
      <section className="register-brand">
        <div className="register-shield">
          <Shield size={42} />
        </div>

        <h1>ZUKA</h1>
        <p className="register-subtitle">SECURITY OPERATIONS CENTER</p>
        <p className="register-description">
          Create your ZUKA account and verify your email.
        </p>

        <div className="security-status">
          <span />
          SECURE SOC ENVIRONMENT
        </div>
      </section>

      <section className="register-container">
        <div className="register-card">
          {/* MOBILE COMPACT BRAND BADGE */}
          <div className="register-mobile-brand">
            <div className="register-mobile-shield">
              <Shield size={24} />
            </div>
            <div className="register-mobile-titles">
              <span className="register-mobile-name">ZUKA</span>
              <span className="register-mobile-sub">
                SECURITY OPERATIONS CENTER
              </span>
            </div>
          </div>

          <div className="register-header">
            <p className="register-eyebrow">
              {view === "form" ? "ACCOUNT REGISTRATION" : "EMAIL VERIFICATION"}
            </p>

            <h2>
              {view === "form" ? "Create your account" : "Verify your email"}
            </h2>

            <p>
              {view === "form"
                ? "Register for access to the ZUKA Security Operations Center."
                : `Enter the 6-digit code sent to ${email}.`}
            </p>
          </div>

          {error && (
            <div className="register-error">
              <strong>Registration notice</strong>
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div
              className="register-success"
              style={{ display: "flex", alignItems: "flex-start", gap: 8 }}
            >
              <CheckCircle2 size={17} />
              <span>{success}</span>
            </div>
          )}

          {view === "form" ? (
            <form onSubmit={handleSubmit}>
              <label htmlFor="username">Username</label>
              <div className="input-wrapper">
                <User size={17} />
                <input
                  id="username"
                  type="text"
                  placeholder="Choose a username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  minLength={3}
                  maxLength={50}
                  autoComplete="username"
                  disabled={loading}
                  required
                />
              </div>

              <label htmlFor="email">Email</label>
              <div className="input-wrapper">
                <Mail size={17} />
                <input
                  id="email"
                  type="email"
                  placeholder="Enter your email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                  disabled={loading}
                  required
                />
              </div>

              <p>
                New accounts have read-only access. Ask an administrator for
                analyst access.
              </p>

              <label htmlFor="password">Password</label>
              <div className="input-wrapper">
                <LockKeyhole size={17} />
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Create a password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  minLength={8}
                  maxLength={128}
                  autoComplete="new-password"
                  disabled={loading}
                  required
                />
                <button
                  type="button"
                  className="password-toggle-btn"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  title={showPassword ? "Hide password" : "Show password"}
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
              <PasswordRequirements password={password} />

              <label htmlFor="confirm-password">Confirm Password</label>
              <div className="input-wrapper">
                <LockKeyhole size={17} />
                <input
                  id="confirm-password"
                  type={showConfirmPassword ? "text" : "password"}
                  placeholder="Confirm your password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  minLength={8}
                  maxLength={128}
                  autoComplete="new-password"
                  disabled={loading}
                  required
                />
                <button
                  type="button"
                  className="password-toggle-btn"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  aria-label={
                    showConfirmPassword ? "Hide password" : "Show password"
                  }
                  title={
                    showConfirmPassword ? "Hide password" : "Show password"
                  }
                  tabIndex={-1}
                >
                  {showConfirmPassword ? (
                    <EyeOff size={18} />
                  ) : (
                    <Eye size={18} />
                  )}
                </button>
              </div>

              <button
                type="submit"
                className="register-button"
                disabled={loading}
              >
                {loading ? "Creating account..." : "Create ZUKA Account"}
              </button>
            </form>
          ) : (
            <form onSubmit={handleVerify}>
              <label htmlFor="verification-email">Registered Email</label>
              <div className="input-wrapper">
                <Mail size={17} />
                <input
                  id="verification-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={loading}
                  required
                />
              </div>

              <label
                style={{
                  display: "block",
                  textAlign: "center",
                  marginBottom: "8px",
                  color: "#38bdf8",
                  fontWeight: 700,
                }}
              >
                6-Digit Verification Code
              </label>
              <OtpInput
                value={otp}
                onChange={(val) => {
                  setOtp(val);
                  setError("");
                }}
                disabled={loading}
              />

              <button
                type="submit"
                className="register-button"
                disabled={loading}
              >
                {loading ? "Verifying..." : "Verify Email"}
              </button>

              <button
                type="button"
                className="back-login"
                onClick={handleResend}
                disabled={loading || resendSeconds > 0}
              >
                {resendSeconds > 0
                  ? `Resend code in ${resendSeconds}s`
                  : "Resend verification code"}
              </button>
            </form>
          )}

          <button
            type="button"
            className="back-login"
            onClick={() => navigate("/login")}
            disabled={loading}
          >
            Already have an account? Sign in
          </button>

          <div className="register-footer">
            <Shield size={14} />
            <span>
              All accounts activate immediately upon 6-digit email OTP
              verification.
            </span>
          </div>
        </div>

        <p className="copyright">ZUKA SOC • Security Intelligence Platform</p>
      </section>
    </main>
  );
}

export default Register;
