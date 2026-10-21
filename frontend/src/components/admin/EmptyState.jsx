import "./EmptyState.css";
import Icons from "../common/Icons.jsx";

export default function EmptyState({ title, description }) {
  return (
    <div className="admin-empty">
      <Icons />
      <h2>{title}</h2>
      {description && <p>{description}</p>}
    </div>
  );
}
