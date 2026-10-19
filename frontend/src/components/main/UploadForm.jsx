import { useRef, useState } from "react";

import "./UploadForm.css";
import Icons from "../Icons.jsx";

export default function UploadForm({ onStartConversationWithFile }) {
  const input = useRef(null);
  const submittingRef = useRef(false); // 중복 업로드 요청을 막는 잠금 값

  const [submitting, setSubmitting] = useState(false);
  const [file, setFile] = useState(null);
  const [drag, setDrag] = useState(false);
  const [error, setError] = useState("");
  const [visibility, setVisibility] = useState("private");

  function select(selectedFile) {
    if (!selectedFile || submittingRef.current) return;
    if (!/\.(pdf|png|jpg|jpeg|txt|md)$/i.test(selectedFile.name)) {
      setError("PDF, PNG, JPG, JPEG, TXT 또는 MD 파일을 선택해주세요.");
      return;
    }
    if (selectedFile.size > 10 * 1024 * 1024) {
      setError("10MB 이하의 파일을 선택해주세요.");
      return;
    }

    setError("");
    setFile(selectedFile);
  }

  async function startConversationWithFile() {
    if (!file || submittingRef.current) return;
    submittingRef.current = true;

    setSubmitting(true);
    setError("");
    try {
      await onStartConversationWithFile({ file, visibility });
    } catch (error) {
      const detail = error.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : "대화를 생성하지 못했습니다. 잠시 후 다시 시도해주세요.",
      );
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  }

  return (
    <>
      <section className="welcome">
        <div className="welcome-symbol">
          <Icons type="spark" />
        </div>

        <p className="headingCaption">YOUR EDITORIAL PARTNER</p>
        <h1>검토할 기사를 올려주세요</h1>

        <div
          className={`upload-area ${drag ? "dragging" : ""} ${file ? "has-file" : ""}`}
          onDragOver={(event) => {
            event.preventDefault();
            setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDrag(false);
            select(event.dataTransfer.files[0]);
          }}
        >
          {file ? (
            <>
              <span className="file-icon">
                <Icons />
              </span>
              <strong>{file.name}</strong>
              <small>{(file.size / 1024).toFixed(1)} KB · 선택한 파일</small>
              <button
                className="change-file"
                disabled={submitting}
                onClick={() => input.current.click()}
              >
                다른 파일 선택
              </button>
            </>
          ) : (
            <>
              <span className="upload-icon">
                <Icons type="upload" />
              </span>
              <strong>기사 파일을 이곳에 놓아주세요</strong>
              <p>또는 아래 버튼으로 파일을 선택하세요</p>
              <button
                className="file-picker"
                disabled={submitting}
                onClick={() => input.current.click()}
              >
                파일 선택
              </button>
              <small>PDF · PNG · JPG · JPEG · TXT · MD / 최대 10MB</small>
            </>
          )}
        </div>

        <input
          ref={input}
          type="file"
          disabled={submitting}
          accept=".pdf,.png,.jpg,.jpeg,.txt,.md"
          aria-label="기사 파일 업로드"
          className="hidden-input"
          onChange={(event) => select(event.target.files[0])}
        />

        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}

        <fieldset className="visibility-options" disabled={submitting}>
          <legend>문서 공개 범위</legend>

          <label
            className={
              visibility === "private" ? "visibility-choice selected" : "visibility-choice"
            }
          >
            <input
              type="radio"
              name="visibility"
              value="private"
              checked={visibility === "private"}
              onChange={() => setVisibility("private")}
            />
            <span>
              <strong>개인</strong>
              <small>나만 볼 수 있는 문서</small>
            </span>
          </label>

          <label
            className={visibility === "public" ? "visibility-choice selected" : "visibility-choice"}
          >
            <input
              type="radio"
              name="visibility"
              value="public"
              checked={visibility === "public"}
              onChange={() => setVisibility("public")}
            />
            <span>
              <strong>공개</strong>
              <small>다른 사용자도 볼 수 있는 문서</small>
            </span>
          </label>
        </fieldset>

        <button
          className="primary start"
          disabled={!file || submitting}
          onClick={startConversationWithFile}
        >
          {submitting ? "파일 처리 중..." : "이 파일로 대화 시작"}
          <Icons type="arrow" />
        </button>
      </section>
    </>
  );
}
