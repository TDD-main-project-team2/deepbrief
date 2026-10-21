import "./MenuContent.css";
import Icons from "../common/Icons.jsx";

const TABS = [
  { id: "members", label: "회원 관리", icon: "users" },
  { id: "templates", label: "템플릿 관리", icon: "file" },
  { id: "guidelines", label: "지침 관리", icon: "clipboardCheck" },
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
              <Icons type={tab.icon} />
            </span>
            {tab.label}
            {activeTab === tab.id && <span className="admin-nav-active-mark" />}
          </button>
        ))}
      </nav>
    </>
  );
}
