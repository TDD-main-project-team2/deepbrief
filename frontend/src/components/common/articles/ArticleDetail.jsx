import ArchivePreview from "../../main/ArchivePreview.jsx";
import "../../main/ArticlePanel.css";

export default function ArticleDetail({ article, ...previewProps }) {
  return (
    <div className="article-detail-main split-main">
      <ArchivePreview
        article={article}
        file={article?.file}
        visibility={article?.visibility}
        previewText={article?.body}
        {...previewProps}
      />
    </div>
  );
}
