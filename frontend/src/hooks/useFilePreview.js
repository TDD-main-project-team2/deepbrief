import { useEffect, useRef, useState } from "react";

export default function useFilePreview() {
  const previewUrlRef = useRef("");
  const previewRequestRef = useRef(0);

  const [previewUrl, setPreviewUrl] = useState("");
  const [previewText, setPreviewText] = useState("");
  const [previewError, setPreviewError] = useState("");
  const [file, setFile] = useState(null);

  useEffect(() => {
    return () => {
      previewRequestRef.current += 1;

      if (previewUrlRef.current) {
        URL.revokeObjectURL(previewUrlRef.current);
        previewUrlRef.current = "";
      }
    };
  }, []);

  async function changeFile(nextFile) {
    // 이전 URL 해제, 새 미리보기 생성 및 텍스트 읽기를 처리합니다.

    const requestId = ++previewRequestRef.current;
    const url = nextFile ? URL.createObjectURL(nextFile) : "";

    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current);
    }
    previewUrlRef.current = url;

    setFile(nextFile);
    setPreviewUrl(url);
    setPreviewText("");
    setPreviewError("");

    if (!nextFile || !/\.(txt|md)$/i.test(nextFile.name)) return;

    try {
      const documentText = await nextFile.text();
      if (previewRequestRef.current === requestId) {
        setPreviewText(documentText);
      }
    } catch {
      if (previewRequestRef.current === requestId) {
        setPreviewError(
          "파일을 읽지 못했습니다. 다른 파일로 다시 시작해주세요.",
        );
      }
    }
  }

  return {
    file,
    previewUrl,
    previewText,
    previewError,
    setPreviewError,
    changeFile,
  };
}
