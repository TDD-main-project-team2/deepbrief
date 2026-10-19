import "./ArchiveMenuItem.css";

export default function ArchiveMenuItem({
  label,
  scopeLabel,
  count,
  selected,
  onClick,
}) {
  return (
    <button
      className={`archive-link ${selected ? "active" : ""}`}
      onClick={onClick}
      aria-current={selected ? "page" : undefined}
    >
      {label}
      <small>{scopeLabel}</small>
      {count != null && <span>{count}</span>}
    </button>
  );
}
