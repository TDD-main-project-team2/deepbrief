import { useState } from "react";
import { Link } from "react-router";

import "./SideMenu.css";
import brandIcon from "../../assets/svg/icon-gradient.svg";

import ArchiveMenuItem from "./ArchiveMenuItem.jsx";
import ConversationMenuItem from "./ConversationMenuItem.jsx";
import Icons from "../Icons.jsx";

export default function SideMenu({
  menuOpen,
  setMenuOpen,
  onStartNewConversation,
  articles,
  view,
  activeConversationId,
  conversations,
  openChat,
  onDeleteConversation,
  setView,
  user,
  onLogout,
}) {
  const [chatsOpen, setChatsOpen] = useState(true);
  const [articlesOpen, setArticlesOpen] = useState(true);

  return (
    <>
      <button
        className="menu-toggle"
        aria-label={menuOpen ? "메뉴 닫기" : "메뉴 열기"}
        aria-expanded={menuOpen}
        aria-controls="main-menu"
        onClick={() => setMenuOpen((isOpen) => !isOpen)}
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
        >
          <rect x="3" y="4" width="18" height="16" rx="2" />
          <path d="M9 4v16" />
        </svg>
      </button>

      <aside id="main-menu" className="sidebar">
        <Link className="brand" to="/" onClick={onStartNewConversation}>
          <img className="brand-icon" src={brandIcon} alt="" />
          DeepBrief<span className="brand-dot">.</span>
        </Link>

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
                    const article = articles.find(
                      (article) => article.id === conversation.articleId,
                    );

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
                  scopeLabel="전체"
                  count={articles.length}
                  selected={view === "private"}
                  onClick={() => setView("private")}
                />
                <ArchiveMenuItem
                  label="사내 기사"
                  scopeLabel="준비 중"
                  selected={view === "public"}
                  onClick={() => setView("public")}
                />
              </div>
            )}
          </section>
        </nav>

        <div className="sidebar-bottom">
          <div className="user-profile" aria-label={user ? "로그인 사용자" : "비로그인 사용자"}>
            <div className="user-details">
              <strong>{user ? user.nickname : "Guest"}</strong>
              <small title={user?.email}>{user ? user.email : "로그인 후 이용해 주세요"}</small>
            </div>
          </div>

          {user ? (
            <button className="account-logout" onClick={onLogout}>
              로그아웃
            </button>
          ) : (
            <div className="guest-actions">
              <Link to="/login">로그인</Link>
              <Link to="/signup">회원가입</Link>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
