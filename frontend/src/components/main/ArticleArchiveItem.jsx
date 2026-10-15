import "./ArticleArchiveItem.css";
import Icons from "../Icons.jsx";

export default function ArticleArchiveItem({ article, onOpen }) {
  return (
    <button className="archive-article" onClick={() => onOpen(article)}>
      <span className="file-icon">
        <Icons />
      </span>

      <span className="archive-info">
        <strong>{article.file.name}</strong>
        <small>
          {article.file.name.split(".").pop().toUpperCase()} ·{" "}
          {(article.file.size / 1024).toFixed(1)} KB · {new Date(article.createdAt).toLocaleString("ko-KR")}
        </small>
      </span>
      <span className="archive-open">열기 ↗</span>
    </button>
  );
}
