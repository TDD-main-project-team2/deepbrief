import DeleteButton from "../buttons/DeleteButton.jsx";
import "./ArticleListItem.css";
import Icons from "../Icons.jsx";
import formatDateTime from "../../../utils/formatDateTime.js";

export default function ArticleListItem({ article, onOpen, onDelete, actions, details }) {
  return (
    <div className="archive-article">
      <button type="button" className="archive-item-open" onClick={() => onOpen(article)}>
        <span className="file-icon">
          <Icons />
        </span>

        <span className="archive-info">
          <strong>{article.title || article.file?.name || "제목 없는 기사"}</strong>
          <small>{formatDateTime(article.createdAt ?? article.created_at)}</small>
        </span>
        {details && <span className="archive-item-details">{details}</span>}
        <span className="archive-open">열기 ↗</span>
      </button>

      {(actions || onDelete) && (
        <div className="archive-item-actions">
          {actions}
          {onDelete && (
            <DeleteButton label={`${article.title} 기사 삭제`} onClick={() => onDelete(article)} />
          )}
        </div>
      )}
    </div>
  );
}
