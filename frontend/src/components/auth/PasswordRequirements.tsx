import { Check, X } from "lucide-react";
import "./PasswordRequirements.css";

export interface PasswordRule {
  id: string;
  label: string;
  met: boolean;
}

export interface PasswordValidationResult {
  isValid: boolean;
  score: number;
  strengthLabel: "Too Weak" | "Weak" | "Fair" | "Strong";
  strengthColor: string;
  rules: PasswordRule[];
  firstError: string | null;
}

export function evaluatePassword(password: string): PasswordValidationResult {
  const pwd = password || "";

  const rules: PasswordRule[] = [
    {
      id: "firstCapital",
      label: "First letter must be a capital letter (A-Z)",
      met: /^[A-Z]/.test(pwd),
    },
    {
      id: "minLength",
      label: "Minimum 8 characters in length",
      met: pwd.length >= 8,
    },
    {
      id: "hasLower",
      label: "At least one lowercase letter (a-z)",
      met: /[a-z]/.test(pwd),
    },
    {
      id: "hasDigit",
      label: "At least one numeric number (0-9)",
      met: /\d/.test(pwd),
    },
    {
      id: "hasSpecial",
      label: "At least one special character (!@#$%^&* etc.)",
      met: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?~`]/.test(pwd),
    },
  ];

  const metCount = rules.filter((r) => r.met).length;
  const isValid = metCount === rules.length;

  let strengthLabel: "Too Weak" | "Weak" | "Fair" | "Strong" = "Too Weak";
  let strengthColor = "#ef4444";

  if (metCount >= 5) {
    strengthLabel = "Strong";
    strengthColor = "#10b981";
  } else if (metCount >= 4) {
    strengthLabel = "Fair";
    strengthColor = "#38bdf8";
  } else if (metCount >= 2) {
    strengthLabel = "Weak";
    strengthColor = "#f59e0b";
  }

  const unmet = rules.find((r) => !r.met);
  const firstError = unmet ? unmet.label : null;

  return {
    isValid,
    score: metCount,
    strengthLabel,
    strengthColor,
    rules,
    firstError,
  };
}

interface PasswordRequirementsProps {
  password: string;
  showAlways?: boolean;
}

export default function PasswordRequirements({
  password,
  showAlways = false,
}: PasswordRequirementsProps) {
  if (!password && !showAlways) {
    return null;
  }

  const result = evaluatePassword(password);
  const percent = (result.score / result.rules.length) * 100;

  return (
    <div className="pwd-req-container">
      <div className="pwd-strength-bar-wrapper">
        <div className="pwd-strength-header">
          <span className="pwd-strength-title">Security Complexity</span>
          <span
            className="pwd-strength-badge"
            style={{ color: result.strengthColor }}
          >
            {password ? result.strengthLabel : "Requirements"}
          </span>
        </div>
        <div className="pwd-strength-track">
          <div
            className="pwd-strength-fill"
            style={{
              width: `${percent}%`,
              backgroundColor: result.strengthColor,
            }}
          />
        </div>
      </div>

      <ul className="pwd-rules-list">
        {result.rules.map((rule) => (
          <li
            key={rule.id}
            className={`pwd-rule-item ${rule.met ? "met" : "unmet"}`}
          >
            <span className="pwd-rule-icon">
              {rule.met ? <Check size={12} strokeWidth={3} /> : <X size={12} strokeWidth={2.5} />}
            </span>
            <span className="pwd-rule-text">{rule.label}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
