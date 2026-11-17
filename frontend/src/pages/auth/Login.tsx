import { useCapabilities } from "../../services/capabilities";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import {
  forgotPassword,
  login,
  resetPassword,
  verifyEmail,
  verifyResetOtp,
  verifyTwoFactorLogin,
} from "../../services/auth";
import OtpInput from "../../components/auth/OtpInput";
import "./Login.css";

type AuthView =
  "login" | "2fa" | "forgot-email" | "forgot-otp" | "reset" | "verify";

function Login() {
  const navigate = useNavigate();
  const capabilities = useCapabilities();
  const location = useLocation();
  const initialState = location.state as {
    email?: string;
    message?: string;
    verifyEmail?: boolean;
  } | null;

  const [view, setView] = useState<AuthView>(() =>
    initialState?.verifyEmail ? "verify" : "login",
  );

  const [usernameOrEmail, setUsernameOrEmail] = useState("");
  const [password, setPassword] = useState("");

  const [email, setEmail] = useState(initialState?.email || "");
  const [otp, setOtp] = useState("");

  const [twoFactorOtp, setTwoFactorOtp] = useState("");
  const [twoFactorChallenge, setTwoFactorChallenge] = useState("");

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [showPassword, setShowPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(initialState?.message || "");
  const [recoveryNotice, setRecoveryNotice] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("zuka_access_token");

    if (token) {
      navigate("/dashboard", { replace: true });
      return;
    }
  }, [navigate]);

  function clearMessages() {
    setError("");
    setSuccess("");
  }

  function clearTwoFactorState() {
    setTwoFactorChallenge("");
    setTwoFactorOtp("");
  }

  function goBackToLogin() {
    clearMessages();
    setRecoveryNotice("");
    setOtp("");
    clearTwoFactorState();
    setView("login");
  }

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (loading) {
      return;
    }

    clearMessages();

    const username = usernameOrEmail.trim();

    if (!username) {
      setError("Please enter your username or email.");
      return;
    }

    if (!password) {
      setError("Please enter your password.");
      return;
    }

    setLoading(true);

    try {
      const result = await login({
        username_or_email: username,
        password,
      });

      /*
       * IMPORTANT SECURITY RULE:
       *
       * When 2FA is enabled, the backend returns a challenge token
       * instead of an access token. Do NOT store any JWT at this stage.
       */
      if (result.requires_two_factor) {
        if (!result.challenge_token) {
          throw new Error(
            "Two-step verification challenge was not created. Please sign in again.",
          );
        }

        setTwoFactorChallenge(result.challenge_token);
        setTwoFactorOtp("");
        setSuccess(
          result.message ||
            "A 6-digit verification code has been sent to your registered email address.",
        );
        setView("2fa");

        return;
      }

      /*
       * Normal login when 2FA is disabled.
       */
      if (!result.access_token || !result.user) {
        throw new Error("Authentication response was incomplete.");
      }

      localStorage.setItem("zuka_access_token", result.access_token);
      localStorage.setItem("zuka_user", JSON.stringify(result.user));

      const state = location.state as { from?: string } | null;
      const requestedPath = state?.from;

      const destination =
        requestedPath &&
        requestedPath.startsWith("/") &&
        !requestedPath.startsWith("//")
          ? requestedPath
          : "/dashboard";

      navigate(destination, { replace: true });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Unable to authenticate.";

      setError(message);

      if (message.toLowerCase().includes("verify your email")) {
        setEmail(username.includes("@") ? username : "");
        setView("verify");
      }

      localStorage.removeItem("zuka_access_token");
      localStorage.removeItem("zuka_user");
    } finally {
      setLoading(false);
    }
  }

  async function handleTwoFactorLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (loading) {
      return;
    }

    clearMessages();

    if (!twoFactorChallenge) {
      setError(
        "Your two-step verification session is missing. Please sign in again.",
      );
      clearTwoFactorState();
      setView("login");
      return;
    }

    if (!/^\d{6}$/.test(twoFactorOtp)) {
      setError(
        "Enter the 6-digit verification code sent to your registered email.",
      );
      return;
    }

    setLoading(true);

    try {
      const result = await verifyTwoFactorLogin({
        challenge_token: twoFactorChallenge,
        otp: twoFactorOtp,
      });

      /*
       * JWT is stored ONLY after successful OTP verification.
       */
      localStorage.setItem("zuka_access_token", result.access_token);
      localStorage.setItem("zuka_user", JSON.stringify(result.user));

      clearTwoFactorState();

      const state = location.state as { from?: string } | null;
      const requestedPath = state?.from;

      const destination =
        requestedPath &&
        requestedPath.startsWith("/") &&
        !requestedPath.startsWith("//")
          ? requestedPath
          : "/dashboard";

      navigate(destination, { replace: true });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Two-step verification failed.";

      setError(message);

      /*
       * Never keep an access token after a failed 2FA attempt.
       */
      localStorage.removeItem("zuka_access_token");
      localStorage.removeItem("zuka_user");
    } finally {
      setLoading(false);
    }
  }

  async function handleForgotEmail(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (loading) {
      return;
    }

    clearMessages();

    const cleanEmail = email.trim();

    if (!cleanEmail) {
      setError("Please enter your account email address.");
      return;
    }

    setLoading(true);

    try {
      const result = await forgotPassword({
        email: cleanEmail,
      });

      setRecoveryNotice(
        result.message ||
          "If an account exists for this email, a password reset code has been sent.",
      );

      setView("forgot-otp");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to start recovery.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifyReset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (loading) {
      return;
    }

    clearMessages();

    if (!/^\d{6}$/.test(otp)) {
      setError("Enter the 6-digit verification code sent to your email.");
      return;
    }

    setLoading(true);

    try {
      const result = await verifyResetOtp({
        email: email.trim(),
        otp,
      });

      setSuccess(result.message || "Code verified. Create your new password.");

      setView("reset");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Invalid verification code.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleResetPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (loading) {
      return;
    }

    clearMessages();

    if (newPassword.length < 8) {
      setError("Password must contain at least 8 characters.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);

    try {
      const result = await resetPassword({
        email: email.trim(),
        otp,
        new_password: newPassword,
      });

      setSuccess(
        result.message || "Password reset successfully. You can now sign in.",
      );

      setPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setOtp("");
      setView("login");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to reset password.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifyEmail(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (loading) {
      return;
    }

    clearMessages();

    if (!email.trim()) {
      setError("Please enter the email used during registration.");
      return;
    }

    if (!/^\d{6}$/.test(otp)) {
      setError("Enter the 6-digit verification code.");
      return;
    }

    setLoading(true);

    try {
      const result = await verifyEmail({
        email: email.trim(),
        otp,
      });

      setSuccess(
        result.message || "Email verified successfully. You can now sign in.",
      );

      setOtp("");
      setUsernameOrEmail(email.trim());
      setView("login");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Email verification failed.",
      );
    } finally {
      setLoading(false);
    }
  }

  const isTwoFactor = view === "2fa";
  const recovery = view !== "login" && view !== "2fa";

  return (
    <main className="login-page">
      <div className="login-layout">
        <section className="login-brand">
          <div className="brand-inner">
            <div className="brand-icon">
              <ShieldCheck size={68} strokeWidth={1.7} />
            </div>

            <div className="brand-logo">ZUKA</div>

            <div className="brand-heading">SECURITY OPERATIONS CENTER</div>

            <p className="brand-description">
              Intelligent network threat detection, investigation and security
              operations.
            </p>

            <div className="secure-badge">
              <span className="secure-indicator" />
              <span>ZUKA WORKSPACE</span>
            </div>
          </div>
        </section>

        <section className="login-panel">
          <div className="login-card">
            {/* MOBILE COMPACT BRAND BADGE */}
            <div className="login-mobile-brand">
              <div className="login-mobile-brand-icon">
                <ShieldCheck size={24} />
              </div>
              <div className="login-mobile-brand-text">
                <span className="login-mobile-logo">ZUKA</span>
                <span className="login-mobile-subtitle">
                  SECURITY OPERATIONS CENTER
                </span>
              </div>
            </div>

            {(recovery || isTwoFactor) && (
              <button
                type="button"
                className="forgot back-button"
                onClick={goBackToLogin}
                disabled={loading}
              >
                <ArrowLeft size={15} />
                Back to sign in
              </button>
            )}

            <div className="login-eyebrow">
              {view === "verify"
                ? "EMAIL VERIFICATION"
                : view === "2fa"
                  ? "SECURITY VERIFICATION"
                  : recovery
                    ? "ACCOUNT RECOVERY"
                    : "AUTHORIZED ACCESS"}
            </div>

            <h1>
              {view === "login" && "Welcome back"}

              {view === "2fa" && "Verify your identity"}

              {view === "verify" && "Verify your email"}

              {view === "forgot-email" && "Reset your password"}

              {view === "forgot-otp" && "Enter verification code"}

              {view === "reset" && "Create a new password"}
            </h1>

            <p className="login-description">
              {view === "login" &&
                "Sign in to access the ZUKA Security Operations Center."}

              {view === "2fa" &&
                "Enter the 6-digit security code sent to your registered email address to complete sign in."}

              {view === "verify" &&
                "Enter the 6-digit code sent to your registered email address."}

              {view === "forgot-email" &&
                "Enter your registered email and ZUKA will send a secure reset code."}

              {view === "forgot-otp" &&
                "Check your email and enter the 6-digit password reset code."}

              {view === "reset" &&
                "Choose a new password for your ZUKA account."}
            </p>

            {error && (
              <div className="login-error">
                <strong>Authentication notice</strong>

                <span>{error}</span>
              </div>
            )}

            {success && (
              <div className="login-success">
                <CheckCircle2 size={18} strokeWidth={2} />

                <span>{success}</span>
              </div>
            )}

            {recoveryNotice && (
              <div className="recovery-notice">{recoveryNotice}</div>
            )}

            {view === "login" && (
              <>
                <form className="login-form" onSubmit={handleLogin}>
                  <div className="field">
                    <label htmlFor="username">Username or Email</label>

                    <div className="input-box">
                      <UserRound size={20} strokeWidth={1.8} />

                      <input
                        id="username"
                        type="text"
                        value={usernameOrEmail}
                        onChange={(e) => {
                          setUsernameOrEmail(e.target.value);
                          setError("");
                        }}
                        placeholder="Enter username or email"
                        autoComplete="username"
                        disabled={loading}
                        autoFocus
                      />
                    </div>
                  </div>

                  <div className="field">
                    <label htmlFor="password">Password</label>

                    <div className="input-box password-input-box">
                      <LockKeyhole size={20} strokeWidth={1.8} />

                      <input
                        id="password"
                        type={showPassword ? "text" : "password"}
                        value={password}
                        onChange={(e) => {
                          setPassword(e.target.value);
                          setError("");
                        }}
                        placeholder="Enter password"
                        autoComplete="current-password"
                        disabled={loading}
                      />

                      <button
                        type="button"
                        className="password-toggle-btn"
                        onClick={() => setShowPassword(!showPassword)}
                        aria-label={
                          showPassword ? "Hide password" : "Show password"
                        }
                        title={showPassword ? "Hide password" : "Show password"}
                        tabIndex={-1}
                      >
                        {showPassword ? (
                          <EyeOff size={18} />
                        ) : (
                          <Eye size={18} />
                        )}
                      </button>
                    </div>
                  </div>

                  <div className="login-options">
                    <button
                      type="button"
                      className="forgot"
                      hidden={!capabilities.password_recovery}
                      disabled={loading}
                      onClick={() => {
                        clearMessages();
                        setRecoveryNotice("");
                        setEmail("");
                        setOtp("");
                        setView("forgot-email");
                      }}
                    >
                      Forgot password?
                    </button>
                  </div>

                  <button
                    type="submit"
                    className="login-submit"
                    disabled={loading}
                  >
                    {loading ? (
                      <>
                        <span className="spinner" />
                        Signing in...
                      </>
                    ) : (
                      "Sign In"
                    )}
                  </button>
                </form>

                <Link
                  to="/register"
                  className="register-link"
                  hidden={!capabilities.registration}
                >
                  New to ZUKA? Create a new account
                </Link>
                {!capabilities.registration && (
                  <p>Need an account? Ask your administrator to create one.</p>
                )}
              </>
            )}

            {view === "2fa" && (
              <>
                <div className="two-factor-panel">
                  <div className="two-factor-icon">
                    <ShieldCheck size={28} strokeWidth={1.8} />
                  </div>

                  <div className="two-factor-content">
                    <strong>Two-step verification required</strong>

                    <p>
                      We sent a 6-digit verification code to your registered
                      email address.
                    </p>
                  </div>
                </div>

                <form className="login-form" onSubmit={handleTwoFactorLogin}>
                  <div className="field" style={{ textAlign: "center" }}>
                    <label
                      style={{
                        display: "block",
                        marginBottom: "8px",
                        color: "#38bdf8",
                        fontWeight: 700,
                      }}
                    >
                      6-Digit Security Code
                    </label>
                    <OtpInput
                      value={twoFactorOtp}
                      onChange={(val) => {
                        setTwoFactorOtp(val);
                        setError("");
                      }}
                      disabled={loading}
                    />
                  </div>

                  <button
                    className="login-submit"
                    type="submit"
                    disabled={loading}
                  >
                    {loading ? (
                      <>
                        <span className="spinner" />
                        Verifying...
                      </>
                    ) : (
                      <>
                        <ShieldCheck size={18} />
                        Verify & Continue
                      </>
                    )}
                  </button>

                  <div className="two-factor-help">
                    <span>Didn't receive the code?</span>

                    <button
                      type="button"
                      className="forgot"
                      hidden={!capabilities.password_recovery}
                      disabled={loading}
                      onClick={async () => {
                        clearMessages();

                        if (!usernameOrEmail.trim()) {
                          setError(
                            "Please return to sign in and enter your username or email.",
                          );
                          return;
                        }

                        /*
                         * The backend login endpoint creates
                         * a fresh 2FA challenge when credentials
                         * are submitted again.
                         */
                        setLoading(true);

                        try {
                          const result = await login({
                            username_or_email: usernameOrEmail.trim(),
                            password,
                          });

                          if (
                            result.requires_two_factor &&
                            result.challenge_token
                          ) {
                            setTwoFactorChallenge(result.challenge_token);

                            setTwoFactorOtp("");

                            setSuccess(
                              result.message ||
                                "A new verification code has been sent to your email.",
                            );
                          } else {
                            setError(
                              "Unable to create a new verification challenge. Please sign in again.",
                            );
                          }
                        } catch (err) {
                          setError(
                            err instanceof Error
                              ? err.message
                              : "Unable to resend the verification code.",
                          );
                        } finally {
                          setLoading(false);
                        }
                      }}
                    >
                      Send a new code
                    </button>
                  </div>
                </form>
              </>
            )}

            {view === "verify" && (
              <form className="login-form" onSubmit={handleVerifyEmail}>
                <div className="field">
                  <label htmlFor="verify-email">Registered Email</label>

                  <div className="input-box">
                    <Mail size={20} />

                    <input
                      id="verify-email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="name@example.com"
                      disabled={loading}
                      required
                      autoFocus
                    />
                  </div>
                </div>

                <div className="field" style={{ textAlign: "center" }}>
                  <label
                    style={{
                      display: "block",
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
                </div>

                <button
                  className="login-submit"
                  type="submit"
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <span className="spinner" />
                      Verifying...
                    </>
                  ) : (
                    "Verify Email"
                  )}
                </button>
              </form>
            )}

            {view === "forgot-email" && (
              <form className="login-form" onSubmit={handleForgotEmail}>
                <div className="field">
                  <label htmlFor="recovery-email">Account Email</label>

                  <div className="input-box">
                    <Mail size={20} />

                    <input
                      id="recovery-email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="name@example.com"
                      autoComplete="email"
                      disabled={loading}
                      required
                      autoFocus
                    />
                  </div>
                </div>

                <button
                  className="login-submit"
                  type="submit"
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <span className="spinner" />
                      Sending code...
                    </>
                  ) : (
                    "Send Reset Code"
                  )}
                </button>
              </form>
            )}

            {view === "forgot-otp" && (
              <form className="login-form" onSubmit={handleVerifyReset}>
                <div className="field" style={{ textAlign: "center" }}>
                  <label
                    style={{
                      display: "block",
                      marginBottom: "8px",
                      color: "#38bdf8",
                      fontWeight: 700,
                    }}
                  >
                    6-Digit Password Reset Code
                  </label>
                  <OtpInput
                    value={otp}
                    onChange={(val) => {
                      setOtp(val);
                      setError("");
                    }}
                    disabled={loading}
                  />
                </div>

                <button
                  className="login-submit"
                  type="submit"
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <span className="spinner" />
                      Checking code...
                    </>
                  ) : (
                    "Verify Code"
                  )}
                </button>
              </form>
            )}

            {view === "reset" && (
              <form className="login-form" onSubmit={handleResetPassword}>
                <div className="field">
                  <label htmlFor="new-password">New Password</label>

                  <div className="input-box password-input-box">
                    <LockKeyhole size={20} />

                    <input
                      id="new-password"
                      type={showNewPassword ? "text" : "password"}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="Minimum 8 characters"
                      autoComplete="new-password"
                      minLength={8}
                      maxLength={128}
                      disabled={loading}
                      required
                      autoFocus
                    />

                    <button
                      type="button"
                      className="password-toggle-btn"
                      onClick={() => setShowNewPassword(!showNewPassword)}
                      aria-label={
                        showNewPassword ? "Hide password" : "Show password"
                      }
                      title={
                        showNewPassword ? "Hide password" : "Show password"
                      }
                      tabIndex={-1}
                    >
                      {showNewPassword ? (
                        <EyeOff size={18} />
                      ) : (
                        <Eye size={18} />
                      )}
                    </button>
                  </div>
                </div>

                <div className="field">
                  <label htmlFor="confirm-new-password">
                    Confirm New Password
                  </label>

                  <div className="input-box password-input-box">
                    <LockKeyhole size={20} />

                    <input
                      id="confirm-new-password"
                      type={showConfirmPassword ? "text" : "password"}
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="Repeat your new password"
                      autoComplete="new-password"
                      minLength={8}
                      maxLength={128}
                      disabled={loading}
                      required
                    />

                    <button
                      type="button"
                      className="password-toggle-btn"
                      onClick={() =>
                        setShowConfirmPassword(!showConfirmPassword)
                      }
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
                </div>

                <button
                  className="login-submit"
                  type="submit"
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <span className="spinner" />
                      Resetting...
                    </>
                  ) : (
                    "Reset Password"
                  )}
                </button>
              </form>
            )}

            {view !== "login" && view !== "verify" && view !== "2fa" && (
              <button
                type="button"
                className="register-link recovery-verify-link"
                onClick={() => {
                  clearMessages();
                  setView("verify");
                  setOtp("");
                }}
                disabled={loading}
              >
                Need to verify a newly created account?
              </button>
            )}

            <div className="login-footer">
              <span className="footer-dot" />
              <span>ZUKA SOC AUTHENTICATION SERVICE</span>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

export default Login;
