import Icons from "../Icons.jsx";
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
        <Icons type="panel" />
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
