import { useState } from "react";

import "./MenuContent.css";

import ArchiveMenuItem from "./ArchiveMenuItem.jsx";
import ConversationMenuItem from "./ConversationMenuItem.jsx";
import Icons from "../common/Icons.jsx";

export default function MenuContent({
  onStartNewConversation,
  articles,
  publicArticleCount,
  view,
  activeConversationId,
  conversations,
  openChat,
  onDeleteConversation,
  setView,
}) {
  const [chatsOpen, setChatsOpen] = useState(true);
  const [articlesOpen, setArticlesOpen] = useState(true);

  return (
    <>
      <button className="new-chat" onClick={onStartNewConversation}>
        <Icons type="plus" />새 대화
      </button>

      <nav className="menu-groups">
        <section className={`menu-section conversation-section ${chatsOpen ? "expanded" : ""}`}>
          <button
            className="menu-group-title"
            aria-expanded={chatsOpen}
            onClick={() => setChatsOpen((isOpen) => !isOpen)}
          >
            <Icons type="chat" />
            대화
            <span className="menu-chevron">
              <Icons type={chatsOpen ? "chevronDown" : "chevronRight"} />
            </span>
          </button>

          {chatsOpen && (
            <div className="chat-history">
              {conversations.length ? (
                conversations.map((conversation) => {
                  const article = articles.find((article) => article.id === conversation.articleId);

                  return (
                    <ConversationMenuItem
                      key={conversation.id}
                      conversation={conversation}
                      article={article}
                      selected={view === "chat" && activeConversationId === conversation.id}
                      onOpen={openChat}
                      onDelete={onDeleteConversation}
                    />
                  );
                })
              ) : (
                <p className="no-chats">아직 대화 기록이 없어요.</p>
              )}
            </div>
          )}
        </section>

        <section className="menu-section articles-section">
          <button
            className="menu-group-title"
            aria-expanded={articlesOpen}
            onClick={() => setArticlesOpen((isOpen) => !isOpen)}
          >
            <Icons />
            보관함
            <span className="menu-chevron">
              <Icons type={articlesOpen ? "chevronDown" : "chevronRight"} />
            </span>
          </button>

          {articlesOpen && (
            <div className="article-submenus">
              <ArchiveMenuItem
                label="내 기사"
                count={articles.length}
                selected={view === "private"}
                onClick={() => setView("private")}
              />
              <ArchiveMenuItem
                label="사내 기사"
                count={publicArticleCount}
                selected={view === "public"}
                onClick={() => setView("public")}
              />
            </div>
          )}
        </section>
      </nav>
    </>
  );
}
