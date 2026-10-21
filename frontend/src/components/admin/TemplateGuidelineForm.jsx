import { useState } from "react";

export default function TemplateGuidelineForm({
  initialValue,
  resourceLabel,
  onCancel,
  onSubmit,
  saving,
}) {
  const [title, setTitle] = useState(initialValue?.title || "");
  const [content, setContent] = useState(initialValue?.content || "");
  const isEditing = Boolean(initialValue);

  function submit(event) {
    event.preventDefault();
    if (!title.trim() || !content.trim()) return;
    onSubmit({ title: title.trim(), content: content.trim() });
  }

  return (
    <form className="admin-form" onSubmit={submit}>
      <label>
        이름
        <input
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          maxLength={255}
          required
          placeholder={`${resourceLabel} 이름`}
        />
      </label>

      <label>
        내용
        <textarea
          value={content}
          onChange={(event) => setContent(event.target.value)}
          required
          rows={7}
          placeholder={`${resourceLabel} 내용을 입력하세요.`}
        />
      </label>

      <div className="admin-form-actions">
        <button className="admin-button admin-button-secondary" type="button" onClick={onCancel}>
          취소
        </button>
        <button
          className="admin-button admin-button-primary"
          type="submit"
          disabled={saving || !title.trim() || !content.trim()}
        >
          {saving ? "저장 중..." : isEditing ? "변경사항 저장" : "만들기"}
        </button>
      </div>
    </form>
  );
}
