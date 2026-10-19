import "./PasswordInput.css";
import AuthError from "./AuthError.jsx";

import { useState } from "react";

export default function PasswordInput({
  label = "비밀번호",
  error,
  name,
  ...inputProps
}) {
  const [visible, setVisible] = useState(false);
  const errorId = `${name}-error`;

  return (
    <label className="auth-field">
      {label}

      <div className={`password-input ${error ? "has-error" : ""}`}>
        <input
          {...inputProps}
          name={name}
          type={visible ? "text" : "password"}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? errorId : undefined}
        />

        <button
          type="button"
          aria-label={`${label} ${visible ? "숨기기" : "보기"}`}
          onClick={() => setVisible((v) => !v)}
        >
          {visible ? "숨기기" : "보기"}
        </button>
      </div>

      <AuthError id={errorId}>{error}</AuthError>
    </label>
  );
}
