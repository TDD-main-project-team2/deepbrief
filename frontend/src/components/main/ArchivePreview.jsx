import Icons from "../common/Icons.jsx";
import "./ArchivePreview.css";
import FilePreview from "./FilePreview.jsx";
import formatDateTime from "../../utils/formatDateTime.js";

export default function ArchivePreview({
  file,
  visibility,
  archiveView,
  setView,
  previewUrl,
  previewText,
  previewError,
  setPreviewError,
  article,
}) {
  return (
    <section className="file-panel" aria-label="보관함 기사 미리보기">
      <div className="upload-record">
        <button className="back-archive" onClick={() => setView(archiveView)}>
          <Icons type="arrowLeft" /> {archiveView === "private" ? "내 기사" : "사내 기사"} 목록
        </button>

        <div className="document-title-row">
          <h1>{article?.title || file.name}</h1>
        </div>

        <dl>
          <div>
            <dt>등록일</dt>
            <dd>{formatDateTime(article?.createdAt)}</dd>
          </div>
          <div>
            <dt>공개 범위</dt>
            <dd>{visibility === "private" ? "개인" : "공용"}</dd>
          </div>
          <div>
            <dt>카테고리</dt>
            <dd>{article?.category || "미분류"}</dd>
          </div>
        </dl>
      </div>

      <FilePreview
        file={file}
        article={article}
        previewUrl={previewUrl}
        previewText={previewText}
        previewError={previewError}
        setPreviewError={setPreviewError}
      />
    </section>
  );
}
