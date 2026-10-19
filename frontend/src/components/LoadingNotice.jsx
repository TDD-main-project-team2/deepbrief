import "./LoadingNotice.css";

export default function LoadingNotice({ children = "불러오는 중...", className = "" }) {
  return (
    <div className={`loading-notice ${className}`} role="status">
      <span className="loading-notice-spinner" aria-hidden="true" />
      <span>{children}</span>
    </div>
  );
}
