import { adminMenuItems } from "../../config/adminMenuConfig.js";
import "./MenuContent.css";
import Icons from "../common/Icons.jsx";

export default function MenuContent({ activeTab, onSelect }) {
  return (
    <>
      <nav className="admin-nav" aria-label="관리자 메뉴">
        {adminMenuItems.map((tab) => (
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
