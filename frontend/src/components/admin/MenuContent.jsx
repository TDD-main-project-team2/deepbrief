import "./MenuContent.css";

const TABS = [
  { id: "members", label: "회원 관리", icon: "users" },
  { id: "templates", label: "템플릿 관리", icon: "file-text" },
  { id: "guidelines", label: "작성 지침", icon: "clipboard-check" },
  { id: "articles", label: "기사 관리", icon: "newspaper" },
  { id: "settings", label: "조직 설정", icon: "settings" },
];

export default function MenuContent({ activeTab, onSelect }) {
  return (
    <>
      <nav className="admin-nav" aria-label="관리자 메뉴">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`admin-nav-item ${activeTab === tab.id ? "active" : ""}`}
            onClick={() => onSelect(tab)}
          >
            <span className="admin-nav-icon" aria-hidden="true">
              {
                {
                  users: "♙",
                  "file-text": "▤",
                  "clipboard-check": "✓",
                  newspaper: "▥",
                  settings: "⚙",
                }[tab.icon]
              }
            </span>
            {tab.label}
            {activeTab === tab.id && <span className="admin-nav-active-mark" />}
          </button>
        ))}
      </nav>
    </>
  );
}
