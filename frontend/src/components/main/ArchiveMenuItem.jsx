import "./ArchiveMenuItem.css";

export default function ArchiveMenuItem({
  label,
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
      {count != null && <span>{count}</span>}
    </button>
  );
}
