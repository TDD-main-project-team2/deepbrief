import { Link } from "react-router";
import "./MainMenu.css";
import Icons from "../Icons.jsx";
import brandIcon from "../../assets/svg/icon-gradient.svg";

export default function MainMenu({
  menuOpen,
  setMenuOpen,
  reset,
  chatsOpen,
  setChatsOpen,
  articlesOpen,
  setArticlesOpen,
  archive,
  view,
  activeId,
  openChat,
  setView,
  user,
  onLogout,
}) {
  return (
    <>
      <button
        className="menu-toggle"
        aria-label={menuOpen ? "메뉴 닫기" : "메뉴 열기"}
        aria-expanded={menuOpen}
        aria-controls="main-menu"
        onClick={() => setMenuOpen((v) => !v)}
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
        <Link className="brand" to="/" onClick={reset}>
          <img className="brand-icon" src={brandIcon} alt="" />
          DeepBrief<span className="brand-dot">.</span>
        </Link>

        <button className="new-chat" onClick={reset}>
          <Icons type="plus" />새 대화
        </button>

        <nav className="menu-groups">
          <section
            className={`menu-section conversation-section ${chatsOpen ? "expanded" : ""}`}
          >
            <button
              className="menu-group-title"
              aria-expanded={chatsOpen}
              onClick={() => setChatsOpen((v) => !v)}
            >
              <Icons type="chat" />
              대화<span>{chatsOpen ? "⌄" : "›"}</span>
            </button>

            {chatsOpen && (
              <div className="chat-history">
                {archive.length ? (
                  archive.map((a) => (
                    <button
                      key={a.id}
                      className={`history-item ${view === "chat" && activeId === a.id ? "active" : ""}`}
                      onClick={() => openChat(a)}
                      title={a.file.name}
                    >
                      <span>
                        {a.file.name}
                        <small>{a.date}</small>
                      </span>
                    </button>
                  ))
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
              onClick={() => setArticlesOpen((v) => !v)}
            >
              <Icons />
              기사<span>{articlesOpen ? "⌄" : "›"}</span>
            </button>

            {articlesOpen && (
              <div className="article-submenus">
                <button
                  className={
                    view === "private" ? "archive-link active" : "archive-link"
                  }
                  onClick={() => setView("private")}
                >
                  내 기사 <small>개인</small>
                  <span>
                    {archive.filter((a) => a.visibility === "private").length}
                  </span>
                </button>

                <button
                  className={
                    view === "public" ? "archive-link active" : "archive-link"
                  }
                  onClick={() => setView("public")}
                >
                  사내 기사 <small>공용</small>
                  <span>
                    {archive.filter((a) => a.visibility === "public").length}
                  </span>
                </button>
              </div>
            )}
          </section>
        </nav>

        <div className="sidebar-bottom">
          <div
            className="user-profile"
            aria-label={user ? "로그인 사용자" : "비로그인 사용자"}
          >
            <div className="user-details">
              <strong>{user ? user.nickname : "게스트"}</strong>
              <small title={user?.email}>
                {user ? user.email : "로그인하지 않은 상태"}
              </small>
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
