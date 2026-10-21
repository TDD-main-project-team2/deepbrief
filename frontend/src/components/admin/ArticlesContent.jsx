import { useState } from "react";

import "./AdminCommon.css";
import "./ArticlesContent.css";

import ContentHeader from "../common/ContentHeader.jsx";
import EditButton from "../common/buttons/EditButton.jsx";
import DeleteButton from "../common/buttons/DeleteButton.jsx";
import Icons from "../common/Icons.jsx";
import Select from "../common/Select.jsx";
import LoadingNotice from "../common/feedback/LoadingNotice.jsx";
import CompletionNotice from "../common/feedback/CompletionNotice.jsx";
import EmptyState from "./EmptyState.jsx";
import Modal from "./Modal.jsx";
import { updateOrgArticle, deleteOrgArticle } from "../../api/admin.js";

export default function ArticlesContent({ articles, loading, onPerform }) {
  const [deleting, setDeleting] = useState(null);
  const [editing, setEditing] = useState(null);
  const [title, setTitle] = useState("");
  const [visibility, setVisibility] = useState("private");
  const [saving, setSaving] = useState(false);

  function startEdit(article) {
    setEditing(article);
    setTitle(article.title || "");
    setVisibility(article.visibility || "private");
  }

  function removeArticle(article) {
    setDeleting(article);
  }

  async function submit(event) {
    event.preventDefault();
    if (!title.trim()) return;
    setSaving(true);
    try {
      const saved = await onPerform(
        () => updateOrgArticle(editing.id, { title: title.trim(), visibility }),
        "기사 정보를 수정했습니다.",
      );
      if (saved !== false) setEditing(null);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="admin-content-section">
      <CompletionNotice
        title="기사를 삭제할까요?"
        message={deleting ? `'${deleting.title || "제목 없는 기사"}' 기사를 삭제합니다.` : ""}
        onClose={() => setDeleting(null)}
        onConfirm={() => {
          if (!deleting) return;
          const id = deleting.id;
          setDeleting(null);
          void onPerform(() => deleteOrgArticle(id), "기사를 삭제했습니다.");
        }}
        confirmLabel="삭제"
      />

      <ContentHeader
        caption="ARTICLE MANAGEMENT"
        title="기사 관리"
        description="조직에서 접근할 수 있는 기사를 확인하고 공개 범위를 관리합니다."
        actions={<strong className="articles-count">{articles.length}개의 기사</strong>}
      />

      <div className={loading || articles.length ? "admin-article-list" : undefined}>
        {loading ? (
          <LoadingNotice>기사 목록을 불러오는 중...</LoadingNotice>
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
                <EditButton
                  label={`${article.title || "제목 없음"} 기사 수정`}
                  onClick={() => startEdit(article)}
                />
                <DeleteButton
                  label={`${article.title || "제목 없음"} 기사 삭제`}
                  onClick={() => removeArticle(article)}
                />
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
            <Select
              label="공개 범위"
              value={visibility}
              onChange={setVisibility}
              options={[
                { value: "private", label: "비공개" },
                { value: "public", label: "조직 공개" },
              ]}
            />
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
