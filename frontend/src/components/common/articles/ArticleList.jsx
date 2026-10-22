import ArticleListItem from "./ArticleListItem.jsx";
import LoadingNotice from "../feedback/LoadingNotice.jsx";
import "./ArticleList.css";

export default function ArticleList({
  articles,
  onOpen,
  onDelete,
  renderActions,
  renderDetails,
  loading,
  emptyState,
}) {
  if (loading) return <LoadingNotice>기사 목록을 불러오는 중...</LoadingNotice>;
  if (!articles.length) return emptyState;

  return (
    <div className="archive-list">
      {articles.map((article) => (
        <ArticleListItem
          key={article.id}
          article={article}
          onOpen={onOpen}
          onDelete={onDelete}
          actions={renderActions?.(article)}
          details={renderDetails?.(article)}
        />
      ))}
    </div>
  );
}
