import "./AuthLayout.css";
import brandIcon from "../assets/svg/icon-gradient.svg";

export default function AuthLayout({
  title,
  headingCaption,
  children,
  authLinkText,
  authLinkLabel,
  authLinkPath,
  navigate,
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
            <a
              href={authLinkPath}
              onClick={(e) => {
                e.preventDefault();
                navigate(authLinkPath);
              }}
            >
              {authLinkLabel}
            </a>
          </p>
        </section>
      </main>
    </div>
  );
}
