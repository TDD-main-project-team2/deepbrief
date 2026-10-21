import { Navigate } from "react-router";

import brandIcon from "./assets/svg/icon-gradient.svg";
import "./ProtectedRoute.css";

import LoadingNotice from "./components/common/feedback/LoadingNotice.jsx";

export default function ProtectedRoute({ user, loading, children }) {
  if (loading) {
    return (
      <div className="session-loading-page">
        <header className="session-loading-header">
          <div className="brand">
            <img className="brand-icon" src={brandIcon} alt="" />
            DeepBrief<span className="brand-dot">.</span>
          </div>
        </header>

        <main className="session-loading-main" aria-labelledby="session-loading-title">
          <section className="session-loading-card">
            <p className="headingCaption">WELCOME BACK</p>
            <h1 id="session-loading-title">잠시만 기다려주세요</h1>
            <LoadingNotice>로그인 확인 중</LoadingNotice>
          </section>
        </main>
      </div>
    );
  }

  if (!user) return <Navigate to="/login" replace />;

  return children;
}
