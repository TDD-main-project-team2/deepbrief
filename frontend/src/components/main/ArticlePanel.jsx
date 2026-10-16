import "./ArticlePanel.css";

import Icons from "../Icons.jsx";
import FilePreview from "./FilePreview.jsx";

export default function ArticlePanel({
  file,
  visibility,
  previewUrl,
  previewText,
  previewError,
  setPreviewError,
}) {
  return (
    <>
      <section className="file-panel" aria-label="업로드한 파일 미리보기">
        <div className="panel-heading document-panel-heading">
          <span>
            <Icons />
            <span className="header-document-info">
              <strong title={file.name}>{file.name}</strong>
              <span>이 대화의 기준 파일</span>
            </span>
          </span>
          <small>{visibility === "private" ? "개인 문서" : "공개 문서"}</small>
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
