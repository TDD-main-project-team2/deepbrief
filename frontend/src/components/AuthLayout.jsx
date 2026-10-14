import { Link } from "react-router";

import "./AuthLayout.css";
import brandIcon from "../assets/svg/icon-gradient.svg";

export default function AuthLayout({
  title,
  headingCaption,
  children,
  authLinkText,
  authLinkLabel,
  authLinkPath,
}) {
  return (
    <div className="auth-page">
      <header className="auth-header">
        <div className="brand auth-brand">
          <img className="brand-icon" src={brandIcon} alt="" />
          DeepBrief<span className="brand-dot">.</span>
        </div>
      </header>

      <main className="auth-main">
        <section className="auth-form-card">
          <p className="headingCaption">{headingCaption}</p>
          <h1>{title}</h1>

          {children}

          <p className="auth-switch">
            {authLinkText}
            <Link to={authLinkPath} className="auth-switch-link">
              {authLinkLabel}
            </Link>
          </p>
        </section>
      </main>
    </div>
  );
}
