import { useEffect, useId, useRef } from "react";

import "./CompletionNotice.css";

export default function CompletionNotice({
  message,
  onClose,
  title = "완료되었습니다",
  onConfirm,
  confirmLabel = "확인",
}) {
  const dialogRef = useRef(null);
  const messageId = useId();

  useEffect(() => {
    const dialog = dialogRef.current;
    if (message && !dialog.open) dialog.showModal();
    if (!message && dialog.open) dialog.close();
  }, [message]);

  return (
    <dialog
      ref={dialogRef}
      className="completion-notice"
      role="alertdialog"
      aria-label={title}
      aria-describedby={messageId}
      onClose={onClose}
    >
      <span className="completion-notice-icon" aria-hidden="true">
        {onConfirm ? "?" : "✓"}
      </span>
      <h2>{title}</h2>
      <p id={messageId}>{message}</p>
      <form method="dialog" className="completion-notice-actions">
        {onConfirm && (
          <button
            type="button"
            className="completion-notice-cancel"
            onClick={() => dialogRef.current.close()}
            autoFocus
          >
            취소
          </button>
        )}
        <button type="submit" className="primary" onClick={onConfirm} autoFocus={!onConfirm}>
          {confirmLabel}
        </button>
      </form>
    </dialog>
  );
}
