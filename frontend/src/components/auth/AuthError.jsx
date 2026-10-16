import "./AuthError.css";

export default function AuthError({ children, id, variant = "field" }) {
  if (!children) return null;

  return (
    <span id={id} className={`auth-error auth-error--${variant}`} role="alert">
      <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <circle cx="10" cy="10" r="7.5" />
        <path d="M10 6v4.5M10 13v1" />
      </svg>
      <span>{children}</span>
    </span>
  );
}
