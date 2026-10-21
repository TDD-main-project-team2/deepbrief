import Icons from "../Icons.jsx";
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
      <Icons type="alert" />
      <span className="error-notice-message">{children}</span>
      {onRetry && (
        <button type="button" onClick={onRetry}>
          {retryLabel}
        </button>
      )}
    </div>
  );
}
