import { useRef, useState } from "react";

import "./UploadForm.css";
import Icons from "../Icons.jsx";

export default function UploadForm({ onCreateConversation }) {
  const input = useRef(null);

  const [file, setFile] = useState(null);
  const [drag, setDrag] = useState(false);
  const [error, setError] = useState("");
  const [visibility, setVisibility] = useState("private");

  function select(selectedFile) {
    if (!selectedFile) return;
    if (!/\.(pdf|png|jpg|jpeg|txt|md)$/i.test(selectedFile.name)) {
      setError("PDF, PNG, JPG, JPEG, TXT 또는 MD 파일을 선택해주세요.");
      return;
    }
    if (selectedFile.size > 20 * 1024 * 1024) {
      setError("20MB 이하의 파일을 선택해주세요.");
      return;
    }
    setError("");
    setFile(selectedFile);
  }

  function createConversation() {
    if (!file) return;
    onCreateConversation({ file, visibility });
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
                onClick={() => input.current.click()}
              >
                파일 선택
              </button>
              <small>PDF · PNG · JPG · JPEG · TXT · MD / 최대 20MB</small>
            </>
          )}
        </div>

        <input
          ref={input}
          type="file"
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

        <fieldset className="visibility-options">
          <legend>문서 공개 범위</legend>

          <label
            className={
              visibility === "private"
                ? "visibility-choice selected"
                : "visibility-choice"
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
            className={
              visibility === "public"
                ? "visibility-choice selected"
                : "visibility-choice"
            }
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

        <button className="primary start" disabled={!file} onClick={createConversation}>
          이 파일로 대화 시작
          <Icons type="arrow" />
        </button>

        <p className="upload-note">파일 한 개를 기준으로 대화합니다.</p>
      </section>
    </>
  );
}
