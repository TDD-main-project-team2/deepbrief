import "./DeleteButton.css";
import Icons from "../Icons.jsx";

export default function DeleteButton({ label, onClick }) {
  return (
    <button
      type="button"
      className="delete-button"
      aria-label={label}
      title={label}
      onClick={onClick}
    >
      <Icons type="trash" />
    </button>
  );
}
