import "./ContentHeader.css";

export default function ContentHeader({ caption, title, description, actions }) {
  return (
    <div className="content-header">
      <div className="content-header-text">
        {caption && <p className="content-header-caption">{caption}</p>}
        <h1 className="content-header-title">{title}</h1>
        {description && <p className="content-header-description">{description}</p>}
      </div>

      {actions && <div className="content-header-actions">{actions}</div>}
    </div>
  );
}
