import { Check, X } from "lucide-react";
import "./PasswordRequirements.css";

import { evaluatePassword } from "../../utils/password";

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
              {rule.met ? (
                <Check size={12} strokeWidth={3} />
              ) : (
                <X size={12} strokeWidth={2.5} />
              )}
            </span>
            <span className="pwd-rule-text">{rule.label}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
