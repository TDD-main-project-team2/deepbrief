import { Link } from "react-router";

import "./UserProfile.css";

export default function UserProfile({ user, onLogout }) {
  const organizationName = user?.organization_name || "소속 조직 정보 없음";

  return (
    <div className="user-account">
      <div className="user-profile" aria-label={user ? "로그인 사용자" : "비로그인 사용자"}>
        <div className="user-details">
          <strong>{user ? user.nickname : "Guest"}</strong>
          <small title={user ? organizationName : undefined}>
            {user ? organizationName : "로그인 후 이용해 주세요"}
          </small>
        </div>
      </div>

      {user ? (
        <button className="account-logout" type="button" onClick={onLogout}>
          로그아웃
        </button>
      ) : (
        <div className="guest-actions">
          <Link to="/login">로그인</Link>
          <Link to="/signup">회원가입</Link>
        </div>
      )}
    </div>
  );
}
