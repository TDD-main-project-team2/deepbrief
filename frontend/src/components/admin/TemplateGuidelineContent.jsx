import { useState } from "react";

import "./AdminCommon.css";
import "./TemplateGuidelineContent.css";

import Icons from "../common/Icons.jsx";
import EditButton from "../common/buttons/EditButton.jsx";
import DeleteButton from "../common/buttons/DeleteButton.jsx";
import ContentHeader from "../common/ContentHeader.jsx";
import EmptyState from "./EmptyState.jsx";
import Modal from "./Modal.jsx";
import TemplateGuidelineForm from "./TemplateGuidelineForm.jsx";

export default function TemplateGuidelineContent({
  type,
  title,
  description,
  items,
  loading,
  onCreate,
  onEdit,
  onDelete,
}) {
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);
  const isGuideline = type === "guidelines";
  const label = isGuideline ? "작성 지침" : "템플릿";

  async function submit(data) {
    setSaving(true);
    try {
      const saved = editing?.id ? await onEdit(editing.id, data) : await onCreate(data);
      if (saved !== false) setEditing(null);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="admin-content-section">
      <ContentHeader
        caption="ORGANIZATION WORKSPACE"
        title={title}
        description={description}
        actions={
          <>
            <strong className="admin-resource-count">
              {items.length}개의 {label}
            </strong>
            <button
              className="admin-button admin-button-primary admin-resource-create"
              type="button"
              onClick={() => setEditing({})}
            >
              <Icons type="plus" /> 새로 만들기
            </button>
          </>
        }
      />

      {loading ? (
        <div className="admin-loading">불러오는 중...</div>
      ) : items.length ? (
        <div className="admin-resource-grid">
          {items.map((item) => (
            <article className="admin-resource-card" key={item.id}>
              <div className="admin-resource-card-top">
                <span className={`admin-resource-icon ${isGuideline ? "guideline" : "template"}`}>
                  <Icons type={isGuideline ? "clipboardCheck" : "file"} />
                </span>
                <div className="admin-resource-actions">
                  <EditButton
                    label={`${item.title || "제목 없음"} 항목 수정`}
                    onClick={() => setEditing(item)}
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
          ))}
        </div>
      ) : (
        <EmptyState
          title={`등록된 ${label}이 없습니다`}
          description="새 항목을 만들어 조직에서 공통으로 사용할 수 있습니다."
        />
      )}

      {editing && (
        <Modal
          title={editing.id ? `${label} 수정` : `새 ${label} 만들기`}
          onClose={() => setEditing(null)}
        >
          <TemplateGuidelineForm
            initialValue={editing.id ? editing : null}
            resourceLabel={label}
            onCancel={() => setEditing(null)}
            onSubmit={submit}
            saving={saving}
          />
        </Modal>
      )}
    </section>
  );
}
