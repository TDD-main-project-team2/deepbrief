import { Link } from "react-router";
import brandIcon from "../../../assets/svg/icon-gradient.svg";
import "./SidebarHeader.css";

export default function SidebarHeader({ onClick }) {
  return (
    <Link
      className="brand sidebar-header"
      to="/"
      onClick={onClick}
      aria-label="DeepBrief 메인으로 이동"
    >
      <img className="brand-icon" src={brandIcon} alt="" />
      <span className="sidebar-header-name">
        DeepBrief<span className="brand-dot">.</span>
      </span>
    </Link>
  );
}
