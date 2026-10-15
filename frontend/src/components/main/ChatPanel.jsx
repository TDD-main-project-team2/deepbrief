import { useEffect, useRef } from "react";

import "./ChatPanel.css";
import Icons from "../Icons.jsx";

const actions = {
  Edit: ["스트레이트로 다듬기", "기획·해설로 다듬기", "인터뷰 형식으로 다듬기"],
  Review: ["중복·유사 기사 검사", "회사 지침으로 평가"],
  Recommend: ["키워드·태그 추천", "제목·부제목 추천", "후속 기사 아이디어"],
};

export default function ChatPanel({
  messages,
  tool,
  setTool,
  text,
  setText,
  send,
}) {
  const messageArea = useRef(null);

  useEffect(() => {
    const area = messageArea.current;
    if (area) {
      const reduceMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)",
      ).matches;
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

            {messages.map((m, i) => (
              <div className="message-pair" key={i}>
                <div className="user-message">{m.question}</div>

                <div className="assistant-message">
                  <span className="assistant-avatar">
                    <Icons type="spark" />
                  </span>
                  <div>
                    <strong>DeepBrief</strong>
                    <p>{m.answer}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="composer">
            <div className="tools" role="tablist" aria-label="작업 선택">
              {Object.keys(actions).map((t) => (
                <button
                  key={t}
                  role="tab"
                  aria-selected={tool === t}
                  className={tool === t ? "selected" : ""}
                  onClick={() => setTool(t)}
                >
                  {t}
                </button>
              ))}
            </div>

            <div className="quick-actions">
              {(actions[tool] || actions.Edit).map((a) => (
                <button key={a} onClick={() => send(a)}>
                  {a}
                  <span>↗</span>
                </button>
              ))}
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                send();
              }}
            >
              <textarea
                aria-label="대화 메시지"
                placeholder="기사에 대한 요청이나 질문을 입력하세요"
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => {
                  if (
                    e.key === "Enter" &&
                    !e.shiftKey &&
                    !e.nativeEvent.isComposing
                  ) {
                    e.preventDefault();
                    send();
                  }
                }}
              />

              <button
                className="primary send"
                aria-label="메시지 보내기"
                disabled={!text.trim()}
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
