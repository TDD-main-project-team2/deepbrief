import "./ConversationMenuItem.css";
import formatDateTime from "../../utils/formatDateTime.js";

export default function ConversationMenuItem({
  conversation,
  article,
  selected,
  onOpen,
}) {
  const title = article?.file.name || "기사를 찾을 수 없습니다";

  return (
    <button
      className={`history-item ${selected ? "active" : ""}`}
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
  );
}
