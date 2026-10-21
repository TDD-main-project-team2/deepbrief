import SidebarHeader from "./SidebarHeader.jsx";
import UserProfile from "./UserProfile.jsx";
import "./SidebarLayout.css";

export default function SidebarLayout({
  children,
  user,
  onLogout,
  onHeaderClick,
  menuOpen,
  onToggle,
  id = "side-menu",
}) {
  return (
    <>
      <button
        className="sidebar-toggle"
        type="button"
        aria-label={menuOpen ? "메뉴 닫기" : "메뉴 열기"}
        aria-expanded={menuOpen}
        aria-controls={id}
        onClick={onToggle}
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          aria-hidden="true"
        >
          <rect x="3" y="4" width="18" height="16" rx="2" />
          <path d="M9 4v16" />
        </svg>
      </button>

      <aside
        id={id}
        className={`sidebar-layout ${menuOpen ? "is-open" : "is-closed"}`}
        inert={!menuOpen}
      >
        <SidebarHeader onClick={onHeaderClick} />

        <div className="sidebar-layout-content">{children}</div>

        <div className="sidebar-layout-profile">
          <UserProfile user={user} onLogout={onLogout} />
        </div>
      </aside>
    </>
  );
}
