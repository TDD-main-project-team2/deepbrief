import "./DeleteButton.css";
import Icons from "../Icons.jsx";

export default function DeleteButton({ label, onClick, disabled = false }) {
  return (
    <button
      type="button"
      className="delete-button"
      aria-label={label}
      title={label}
      disabled={disabled}
      onClick={onClick}
    >
      <Icons type="trash" />
    </button>
  );
}
