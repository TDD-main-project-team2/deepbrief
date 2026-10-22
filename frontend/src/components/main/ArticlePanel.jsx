import "./ArticlePanel.css";

import Icons from "../common/Icons.jsx";
import FilePreview from "./FilePreview.jsx";

export default function ArticlePanel({
  file,
  visibility,
  previewUrl,
  previewText,
  previewError,
  setPreviewError,
  article,
}) {
  return (
    <section className="file-panel" aria-label="업로드한 파일 미리보기">
      <div className="panel-heading document-panel-heading">
        <span>
          <Icons />
          <span className="header-document-info">
            <strong title={article?.title || file.name}>{article?.title || file.name}</strong>
            <span>이 대화의 기준 기사</span>
          </span>
        </span>
        <small>{visibility === "private" ? "개인 문서" : "공개 문서"}</small>
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
