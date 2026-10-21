import "./Archive.css";
import ContentHeader from "../common/ContentHeader.jsx";
import ArchiveItem from "./ArchiveItem.jsx";
import Icons from "../common/Icons.jsx";

export default function Archive({ view, articles, openArticle, onDeleteArticle }) {
  const isPublic = view === "public";

  return (
    <>
      <section className="archive-page">
        <ContentHeader
          caption="ARTICLE ARCHIVE"
          title={isPublic ? "사내 기사" : "내 기사"}
          description={
            isPublic
              ? "우리 조직에서 공개한 기사를 모아볼 수 있어요."
              : "내가 올린 기사를 모아볼 수 있어요."
          }
          actions={
            <>
          <strong>
            {articles.length}
            개의 기사
          </strong>
          <span>{isPublic ? "공용 아카이브" : "내 아카이브"}</span>
            </>
          }
        />



        {articles.length ? (
          <div className="archive-list">
            {articles.map((article) => (
              <ArchiveItem
                key={article.id}
                article={article}
                onOpen={openArticle}
                onDelete={isPublic ? undefined : onDeleteArticle}
              />
            ))}
          </div>
        ) : (
          <div className="archive-empty">
            <Icons />
            <h2>{isPublic ? "공개된 사내 기사가 없어요." : "아직 올린 기사가 없어요."}</h2>
            {!isPublic && <p>새 대화에서 파일을 올리고 공개 범위를 선택해주세요.</p>}
          </div>
        )}
      </section>
    </>
  );
}
