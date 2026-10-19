import "./Archive.css";
import ArchiveItem from "./ArchiveItem.jsx";
import Icons from "../Icons.jsx";

export default function Archive({ view, articles, openArticle, onDeleteArticle }) {
  const isPublic = view === "public";

  return (
    <>
      <section className="archive-page">
        <p className="headingCaption">ARTICLE ARCHIVE</p>
        <h1>{isPublic ? "사내 기사" : "내 기사"}</h1>
        <p className="archive-description">
          {isPublic ? "다른 동료가 올린 사내 기사를 모아볼 수 있어요." : "내가 올린 기사를 모아볼 수 있어요."}
        </p>

        <div className="archive-summary">
          <strong>
            {isPublic ? "—" : articles.length}
            개의 기사
          </strong>
          <span>{isPublic ? "공용 아카이브" : "내 아카이브"}</span>
        </div>

        {isPublic ? (
          <div className="archive-empty">
            <Icons />
            <h2>업데이트 예정입니다.</h2>
          </div>
        ) : articles.length ? (
          <div className="archive-list">
            {articles.map((article) => (
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
            <h2>아직 올린 기사가 없어요.</h2>
            <p>새 대화에서 파일을 올리고 공개 범위를 선택해주세요.</p>
          </div>
        )}
      </section>
    </>
  );
}
