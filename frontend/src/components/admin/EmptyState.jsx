import Icons from "../common/Icons.jsx";

export default function EmptyState({ title, description }) {
  return (
    <div className="admin-empty">
      <span className="admin-empty-mark">
        <Icons type="minus" />
      </span>
      <strong>{title}</strong>
      <p>{description}</p>
    </div>
  );
}
