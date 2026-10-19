import "./Archive.css";
import ArchiveItem from "./ArchiveItem.jsx";
import Icons from "../Icons.jsx";

export default function Archive({ view, articles, openArticle, onDeleteArticle }) {
  const visibleArticles = articles.filter((article) => article.visibility === view);

  return (
    <>
      <section className="archive-page">
        <p className="headingCaption">ARTICLE ARCHIVE</p>
        <h1>{view === "private" ? "내 기사" : "사내 기사"}</h1>
        <p className="archive-description">
          {view === "private"
            ? "개인으로 올린 기사를 모아볼 수 있어요."
            : "공개로 올린 사내 기사를 함께 찾아볼 수 있어요."}
        </p>

        <div className="archive-summary">
          <strong>
            {visibleArticles.length}
            개의 기사
          </strong>
          <span>{view === "private" ? "개인 아카이브" : "공용 아카이브"}</span>
        </div>

        {visibleArticles.length ? (
          <div className="archive-list">
            {visibleArticles.map((article) => (
              <ArchiveItem
                key={article.id}
                article={article}
                onOpen={openArticle}
                onDelete={onDeleteArticle}
              />
            ))}
          </div>
        ) : (
          <div className="archive-empty">
            <Icons />
            <h2>
              {view === "private"
                ? "아직 개인으로 올린 기사가 없어요."
                : "아직 공개로 올린 기사가 없어요."}
            </h2>
            <p>새 대화에서 파일을 올리고 공개 범위를 선택해주세요.</p>
          </div>
        )}
      </section>
    </>
  );
}
