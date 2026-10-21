import DeleteButton from "../common/buttons/DeleteButton.jsx";
import "./ArchiveItem.css";
import Icons from "../common/Icons.jsx";
import formatDateTime from "../../utils/formatDateTime.js";

export default function ArchiveItem({ article, onOpen, onDelete }) {
  return (
    <div className="archive-article">
      <button type="button" className="archive-item-open" onClick={() => onOpen(article)}>
        <span className="file-icon">
          <Icons />
        </span>

        <span className="archive-info">
          <strong>{article.title || article.file.name}</strong>
          <small>{formatDateTime(article.createdAt)}</small>
        </span>
        <span className="archive-open">열기 ↗</span>
      </button>

      {onDelete && (
        <DeleteButton label={`${article.title} 기사 삭제`} onClick={() => onDelete(article)} />
      )}
    </div>
  );
}
