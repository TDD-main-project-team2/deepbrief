import { useState } from "react";

import ContentHeader from "../common/ContentHeader.jsx";
import Icons from "../common/Icons.jsx";
import EmptyState from "./EmptyState.jsx";
import Modal from "./Modal.jsx";

export default function ArticlesContent({ articles, loading, onUpdate, onDelete }) {
  const [editing, setEditing] = useState(null);
  const [title, setTitle] = useState("");
  const [visibility, setVisibility] = useState("private");
  const [saving, setSaving] = useState(false);

  function startEdit(article) {
    setEditing(article);
    setTitle(article.title || "");
    setVisibility(article.visibility || "private");
  }

  async function submit(event) {
    event.preventDefault();
    if (!title.trim()) return;
    setSaving(true);
    try {
      const saved = await onUpdate(editing.id, { title: title.trim(), visibility });
      if (saved !== false) setEditing(null);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="admin-content-section">
      <ContentHeader
        caption="ORGANIZATION WORKSPACE"
        title="기사 관리"
        description="조직에서 접근할 수 있는 기사를 확인하고 공개 범위를 관리합니다."
        actions={<strong>{articles.length}개의 기사</strong>}
      />

      <div className="admin-article-list">
        {loading ? (
          <div className="admin-loading">기사 목록을 불러오는 중...</div>
        ) : articles.length ? (
          articles.map((article) => (
            <article className="admin-article-row" key={article.id}>
              <div className="admin-article-symbol">
                <Icons type="newspaper" />
              </div>
              <div className="admin-article-info">
                <h3>{article.title || "제목 없는 기사"}</h3>
                <p>
                  {article.author || "작성자 미상"}
                  {article.category ? ` · ${article.category}` : ""}
                </p>
              </div>
              <span
                className={`admin-visibility-pill ${article.visibility === "public" ? "public" : ""}`}
              >
                {article.visibility === "public" ? "조직 공개" : "비공개"}
              </span>
              <div className="admin-article-actions">
                <button
                  className="admin-text-button"
                  type="button"
                  onClick={() => startEdit(article)}
                >
                  수정
                </button>
                <button
                  className="admin-text-button danger"
                  type="button"
                  onClick={() => onDelete(article)}
                >
                  삭제
                </button>
              </div>
            </article>
          ))
        ) : (
          <EmptyState
            title="등록된 기사가 없습니다"
            description="관리 가능한 조직 기사가 여기에 표시됩니다."
          />
        )}
      </div>

      {editing && (
        <Modal title="기사 정보 수정" onClose={() => setEditing(null)}>
          <form className="admin-form" onSubmit={submit}>
            <label>
              기사 제목
              <input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                required
                maxLength={255}
              />
            </label>
            <label>
              공개 범위
              <select value={visibility} onChange={(event) => setVisibility(event.target.value)}>
                <option value="private">비공개</option>
                <option value="public">조직 공개</option>
              </select>
            </label>
            <div className="admin-form-actions">
              <button
                className="admin-button admin-button-secondary"
                type="button"
                onClick={() => setEditing(null)}
              >
                취소
              </button>
              <button
                className="admin-button admin-button-primary"
                type="submit"
                disabled={saving || !title.trim()}
              >
                {saving ? "저장 중..." : "변경사항 저장"}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </section>
  );
}
