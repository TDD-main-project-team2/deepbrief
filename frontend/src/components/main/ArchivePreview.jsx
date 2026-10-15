import "./ArchivePreview.css";
import FilePreview from "./FilePreview.jsx";

export default function ArchivePreview({
  file,
  visibility,
  articles,
  articleId,
  setView,
  previewUrl,
  previewText,
  previewError,
  setPreviewError,
}) {
  return (
    <>
      <section className="file-panel" aria-label="보관함 기사 미리보기">
        <div className="upload-record">
          <button className="back-archive" onClick={() => setView(visibility)}>
            ← {visibility === "private" ? "내 기사" : "사내 기사"} 목록
          </button>

          <div className="document-title-row">
            <h1>{file.name.replace(/\.[^.]+$/, "")}</h1>
            <span className="document-tag format-tag">
              {file.name.split(".").pop().toUpperCase()}
            </span>
            <span className="document-tag">
              {(file.size / 1024).toFixed(1)} KB
            </span>
          </div>

          <dl>
            <div>
              <dt>등록일</dt>
              <dd>
                {new Date(articles.find((article) => article.id === articleId)?.createdAt).toLocaleString("ko-KR")}
              </dd>
            </div>
            <div>
              <dt>공개 범위</dt>
              <dd>{visibility === "private" ? "개인" : "공용"}</dd>
            </div>
            <div>
              <dt>카테고리</dt>
              <dd>
                {articles.find((article) => article.id === articleId)
                  ?.category || "미분류"}
              </dd>
            </div>
            <div>
              <dt>등록 사용자</dt>
              <dd>김민서 · minseo@example.com</dd>
            </div>
          </dl>
        </div>

        <FilePreview
          file={file}
          previewUrl={previewUrl}
          previewText={previewText}
          previewError={previewError}
          setPreviewError={setPreviewError}
        />
      </section>
    </>
  );
}
