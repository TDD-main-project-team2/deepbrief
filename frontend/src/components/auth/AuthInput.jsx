import "./AuthInput.css";
import AuthError from "./AuthError.jsx";

export default function AuthInput({ label, error, name, ...inputProps }) {
  const errorId = `${name}-error`;

  return (
    <label className="auth-field">
      {label}

      <input
        {...inputProps}
        name={name}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? errorId : undefined}
      />

      <AuthError id={errorId}>{error}</AuthError>
    </label>
  );
}
