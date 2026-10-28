import LoadingNotice from "../common/feedback/LoadingNotice.jsx";
import CompletionNotice from "../common/feedback/CompletionNotice.jsx";
import { useState } from "react";

import "./AdminCommon.css";
import "./TemplateGuidelineContent.css";

import Icons from "../common/Icons.jsx";
import ContentHeader from "../common/ContentHeader.jsx";
import EmptyState from "./EmptyState.jsx";
import Modal from "./Modal.jsx";
import TemplateGuidelineForm from "./TemplateGuidelineForm.jsx";
import TemplateGuidelineItem from "./TemplateGuidelineItem.jsx";

export default function TemplateGuidelineContent({
  type,
  caption,
  title,
  description,
  items,
  loading,
  onPerform,
  onCreate,
  onEdit,
  onDelete,
}) {
  const [deleting, setDeleting] = useState(null);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);
  const label = type === "guidelines" ? "작성 지침" : "템플릿";

  function removeResource(item) {
    setDeleting(item);
  }

  async function submit(data) {
    setSaving(true);
    try {
      const saved = await onPerform(
        () => (editing?.id ? onEdit(editing.id, data) : onCreate(data)),
        editing?.id ? `${label}을 수정했습니다.` : `${label}을 만들었습니다.`,
      );
      if (saved !== false) setEditing(null);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="admin-content-section">
      <CompletionNotice
        title="항목을 삭제할까요?"
        message={deleting ? `'${deleting.title}' 항목을 삭제합니다.` : ""}
        onClose={() => setDeleting(null)}
        onConfirm={() => {
          if (!deleting) return;
          const id = deleting.id;
          setDeleting(null);
          void onPerform(() => onDelete(id), "삭제했습니다.");
        }}
        confirmLabel="삭제"
      />

      <ContentHeader
        caption={caption}
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
        <LoadingNotice>불러오는 중...</LoadingNotice>
      ) : items.length ? (
        <div className="admin-resource-grid">
          {items.map((item) => (
            <TemplateGuidelineItem
              key={item.id}
              item={item}
              type={type}
              onEdit={setEditing}
              onDelete={removeResource}
            />
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
