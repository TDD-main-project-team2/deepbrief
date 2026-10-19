import "./ErrorNotice.css";

export default function ErrorNotice({
  children,
  onRetry,
  retryLabel = "다시 시도",
  className = "",
}) {
  if (!children) return null;

  return (
    <div className={`error-notice ${className}`} role="alert">
      <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <circle cx="10" cy="10" r="7.5" />
        <path d="M10 6v4.5M10 13v1" />
      </svg>
      <span className="error-notice-message">{children}</span>
      {onRetry && (
        <button type="button" onClick={onRetry}>
          {retryLabel}
        </button>
      )}
    </div>
  );
}
