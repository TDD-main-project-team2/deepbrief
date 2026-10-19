import DeleteButton from "./DeleteButton.jsx";
import "./ConversationMenuItem.css";
import formatDateTime from "../../utils/formatDateTime.js";

export default function ConversationMenuItem({
  conversation,
  article,
  selected,
  onOpen,
  onDelete,
}) {
  const title = article?.file.name || "기사를 찾을 수 없습니다";

  return (
    <div className={`history-item ${selected ? "active" : ""}`}>
      <button
        type="button"
        className="history-open"
        onClick={() => onOpen(conversation)}
        title={title}
        disabled={!article}
        aria-current={selected ? "page" : undefined}
      >
        <span>
          {title}
          <small>{formatDateTime(conversation.createdAt)}</small>
        </span>
      </button>

      <DeleteButton label={`${title} 대화 삭제`} onClick={() => onDelete(conversation)} />
    </div>
  );
}
