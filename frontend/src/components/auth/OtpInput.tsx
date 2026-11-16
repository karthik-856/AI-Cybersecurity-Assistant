import React, { useRef, useEffect } from "react";
import "./OtpInput.css";

interface OtpInputProps {
  value: string;
  onChange: (otp: string) => void;
  length?: number;
  disabled?: boolean;
  autoFocus?: boolean;
}

export default function OtpInput({
  value,
  onChange,
  length = 6,
  disabled = false,
  autoFocus = true,
}: OtpInputProps) {
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  const digits = Array.from({ length }, (_, i) => value[i] || "");

  useEffect(() => {
    if (autoFocus && inputRefs.current[0]) {
      inputRefs.current[0].focus();
    }
  }, [autoFocus]);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>, index: number) {
    const val = e.target.value.replace(/\D/g, "");
    if (!val) {
      // Clear current digit
      const nextDigits = [...digits];
      nextDigits[index] = "";
      onChange(nextDigits.join(""));
      return;
    }

    // Single digit input
    const nextDigits = [...digits];
    nextDigits[index] = val.slice(-1);
    const newOtp = nextDigits.join("");
    onChange(newOtp);

    // Auto-advance
    if (index < length - 1) {
      inputRefs.current[index + 1]?.focus();
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>, index: number) {
    if (e.key === "Backspace") {
      if (!digits[index] && index > 0) {
        // Move back to previous box and focus
        inputRefs.current[index - 1]?.focus();
        const nextDigits = [...digits];
        nextDigits[index - 1] = "";
        onChange(nextDigits.join(""));
      }
    } else if (e.key === "ArrowLeft" && index > 0) {
      inputRefs.current[index - 1]?.focus();
    } else if (e.key === "ArrowRight" && index < length - 1) {
      inputRefs.current[index + 1]?.focus();
    }
  }

  function handlePaste(e: React.ClipboardEvent<HTMLInputElement>) {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, length);
    if (pasted) {
      onChange(pasted);
      const nextFocus = Math.min(pasted.length, length - 1);
      inputRefs.current[nextFocus]?.focus();
    }
  }

  return (
    <div className="zuka-otp-container" onPaste={handlePaste}>
      {Array.from({ length }).map((_, idx) => (
        <input
          key={idx}
          ref={(el) => {
            inputRefs.current[idx] = el;
          }}
          type="text"
          inputMode="numeric"
          pattern="[0-9]*"
          maxLength={1}
          value={digits[idx] || ""}
          onChange={(e) => handleChange(e, idx)}
          onKeyDown={(e) => handleKeyDown(e, idx)}
          disabled={disabled}
          className={`zuka-otp-box ${digits[idx] ? "filled" : ""}`}
          aria-label={`Digit ${idx + 1}`}
          autoComplete="one-time-code"
        />
      ))}
    </div>
  );
}
