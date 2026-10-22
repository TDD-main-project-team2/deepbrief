import Icons from "../Icons.jsx";
import "./EditButton.css";

export default function EditButton({ label, onClick }) {
  return (
    <button
      type="button"
      className="edit-button"
      aria-label={label}
      title={label}
      onClick={onClick}
    >
      <Icons type="edit" />
    </button>
  );
}
