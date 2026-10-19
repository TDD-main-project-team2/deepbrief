import { useEffect, useRef, useState } from "react";

import "./ChatPanel.css";
import Icons from "../Icons.jsx";

const toolButtonLabels = {
  Edit: ["템플릿에 맞춰 다듬기"],
  Review: ["중복·유사 기사 검사", "회사 지침으로 평가"],
  Recommend: ["키워드·태그", "제목·부제목", "헤드라인", "후속 기사 아이디어"],
};

const editActions = { "템플릿에 맞춰 다듬기": "format" };
const reviewActions = { "중복·유사 기사 검사": "duplicate", "회사 지침으로 평가": "evaluation" };
const recommendActions = {
  "키워드·태그": "keywords",
  "제목·부제목": "title",
  "후속 기사 아이디어": "ideas",
};

export default function ChatPanel({ messages, onSendMessage, isSending = false }) {
  const [text, setText] = useState("");
  const [tool, setTool] = useState("Edit");

  function sendMessage(messageText = text, action) {
    if (!messageText.trim() || isSending) return;
    onSendMessage(messageText, action);
    setText("");
  }

  const messageArea = useRef(null);
  const toolNames = Object.keys(toolButtonLabels);
  const suggestions = toolButtonLabels[tool] || toolButtonLabels.Edit;

  useEffect(() => {
    const area = messageArea.current;
    if (area) {
      const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      area.scrollTo({
        top: area.scrollHeight,
        behavior: reduceMotion ? "auto" : "smooth",
      });
    }
  }, [messages]);

  return (
    <>
      <section className="chat-main" aria-label="기사 채팅방">
        <div className="panel-heading">
          <span>
            <Icons type="chat" />
            기사 채팅
          </span>
          <small>AI 파트너</small>
        </div>

        <div className="chat-body">
          <div className="chat-scroll" ref={messageArea}>
            <div className="assistant-opening">
              <span className="assistant-avatar">
                <Icons type="spark" />
              </span>
              <div>
                <strong>DeepBrief</strong>
                <h2>파일을 선택했어요. 어떤 작업을 도와드릴까요?</h2>
                <p>아래 작업을 선택하거나, 궁금한 내용을 직접 입력해주세요.</p>
              </div>
            </div>

            {messages.map((message, messageIndex) => (
              <div className="message-pair" key={messageIndex}>
                {message.question && <div className="user-message">{message.question}</div>}

                {(message.pending || message.error || message.answer) && (
                  <div className="assistant-message">
                    <span className="assistant-avatar">
                      <Icons type="spark" />
                    </span>
                    <div>
                      <strong>DeepBrief</strong>
                      {message.pending ? (
                        <p role="status">{message.pendingText || "요청을 처리하고 있습니다..."}</p>
                      ) : message.error ? (
                        <p role="alert">{message.error}</p>
                      ) : (
                        <p>{message.answer}</p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="composer">
            <div className="tools" role="tablist" aria-label="작업 선택">
              {toolNames.map((toolName) => (
                <button
                  key={toolName}
                  role="tab"
                  aria-selected={tool === toolName}
                  className={tool === toolName ? "selected" : ""}
                  onClick={() => setTool(toolName)}
                >
                  {toolName}
                </button>
              ))}
            </div>

            <div className="quick-actions">
              {suggestions.map((suggestion) => (
                <button
                  key={suggestion}
                  disabled={isSending || (tool === "Recommend" && !recommendActions[suggestion])}
                  title={
                    tool === "Recommend" && !recommendActions[suggestion]
                      ? "헤드라인 추천은 준비 중입니다."
                      : undefined
                  }
                  onClick={() =>
                    sendMessage(
                      suggestion,
                      tool === "Edit"
                        ? editActions[suggestion]
                        : tool === "Review"
                          ? reviewActions[suggestion]
                          : recommendActions[suggestion],
                    )
                  }
                >
                  {suggestion}
                  {tool === "Recommend" && !recommendActions[suggestion] ? " (준비 중)" : ""}
                  <span>↗</span>
                </button>
              ))}
            </div>

            <form
              onSubmit={(event) => {
                event.preventDefault();
                sendMessage();
              }}
            >
              <textarea
                aria-label="대화 메시지"
                placeholder="기사에 대한 요청이나 질문을 입력하세요"
                value={text}
                onChange={(event) => setText(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
                    event.preventDefault();
                    sendMessage();
                  }
                }}
              />

              <button
                className="primary send"
                aria-label="메시지 보내기"
                disabled={isSending || !text.trim()}
              >
                <Icons type="arrow" />
              </button>
            </form>
          </div>
        </div>
      </section>
    </>
  );
}
