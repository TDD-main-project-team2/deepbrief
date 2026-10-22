import "./TemplateGuidelineItem.css";

import Icons from "../common/Icons.jsx";
import EditButton from "../common/buttons/EditButton.jsx";
import DeleteButton from "../common/buttons/DeleteButton.jsx";

export default function TemplateGuidelineItem({ item, type, onEdit, onDelete }) {
  const isGuideline = type === "guidelines";

  return (
    <article className="admin-resource-card">
      <div className="admin-resource-card-top">
        <span className={`admin-resource-icon ${isGuideline ? "guideline" : "template"}`}>
          <Icons type={isGuideline ? "clipboardCheck" : "file"} />
        </span>
        <div className="admin-resource-actions">
          <EditButton
            label={`${item.title || "제목 없음"} 항목 수정`}
            onClick={() => onEdit(item)}
          />
          <DeleteButton
            label={`${item.title || "제목 없음"} 항목 삭제`}
            onClick={() => onDelete(item)}
          />
        </div>
      </div>

      <h3>{item.title}</h3>
      <p className="admin-resource-preview">{item.content}</p>
    </article>
  );
}
