import DeleteButton from "./DeleteButton.jsx";
import "./ArchiveItem.css";
import Icons from "../Icons.jsx";
import formatDateTime from "../../utils/formatDateTime.js";

export default function ArchiveItem({ article, onOpen, onDelete }) {
  return (
    <div className="archive-article">
      <button type="button" className="archive-item-open" onClick={() => onOpen(article)}>
        <span className="file-icon">
          <Icons />
        </span>

        <span className="archive-info">
          <strong>{article.file.name}</strong>
          <small>
            {article.file.name.split(".").pop().toUpperCase()} ·{" "}
            {(article.file.size / 1024).toFixed(1)} KB · {formatDateTime(article.createdAt)}
          </small>
        </span>
        <span className="archive-open">열기 ↗</span>
      </button>

      <DeleteButton label={`${article.file.name} 기사 삭제`} onClick={() => onDelete(article)} />
    </div>
  );
}
