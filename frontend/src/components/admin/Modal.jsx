import "./AdminCommon.css";
import "./Modal.css";
import Icons from "../common/Icons.jsx";

export default function Modal({ title, onClose, children }) {
  return (
    <div
      className="admin-modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section className="admin-modal" role="dialog" aria-modal="true" aria-label={title}>
        <div className="admin-modal-heading">
          <h2>{title}</h2>
          <button className="admin-icon-button" type="button" onClick={onClose} aria-label="닫기">
            <Icons type="close" />
          </button>
        </div>

        {children}
      </section>
    </div>
  );
}
