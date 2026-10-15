import "./FilePreview.css";
import Icons from "../Icons.jsx";

function PdfContent({ previewUrl }) {
  return (
    <object
      className="pdf-preview"
      data={previewUrl}
      type="application/pdf"
      aria-label="PDF 원본 미리보기"
    >
      <div className="preview-fallback">
        <Icons />
        <h2>PDF 미리보기를 표시할 수 없습니다.</h2>
        <a href={previewUrl} target="_blank" rel="noreferrer">
          원본 파일 열기 ↗
        </a>
      </div>
    </object>
  );
}

function TextContent({ file, previewText, previewError }) {
  return (
    <article className="text-paper">
      <p className="paper-label">ORIGINAL DOCUMENT</p>
      <h2>{file.name.replace(/\.[^.]+$/, "")}</h2>
      <pre>{previewError || previewText || "내용이 없는 파일입니다."}</pre>
    </article>
  );
}

function ImageContent({ file, previewUrl, previewError, setPreviewError }) {
  return (
    <div className="image-preview">
      <img
        src={previewUrl}
        alt={file.name}
        onError={(event) => {
          event.currentTarget.style.display = "none";
          setPreviewError("이미지를 표시할 수 없습니다.");
        }}
      />
      {previewError && (
        <p role="alert">이미지를 표시할 수 없습니다. 파일을 확인해주세요.</p>
      )}
    </div>
  );
}

export default function FilePreview(props) {
  const extension = props.file.name.split(".").pop().toLowerCase();

  if (extension === "pdf") {
    return <PdfContent previewUrl={props.previewUrl} />;
  }

  if (extension === "txt" || extension === "md") {
    return (
      <TextContent
        file={props.file}
        previewText={props.previewText}
        previewError={props.previewError}
      />
    );
  }

  if (["png", "jpg", "jpeg"].includes(extension)) {
    return <ImageContent {...props} />;
  }

  return (
    <div className="preview-fallback">
      <p>지원하지 않는 파일 형식입니다.</p>
    </div>
  );
}
