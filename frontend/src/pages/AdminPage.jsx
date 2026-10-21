import { useCallback, useEffect, useState } from "react";
import "./AdminPage.css";
import UserProfile from "../components/common/UserProfile.jsx";
import {
  getOrgMembers,
  updateOrgMember,
  deleteOrgMember,
  getOrgTemplates,
  createOrgTemplate,
  updateOrgTemplate,
  deleteOrgTemplate,
  getOrgGuidelines,
  createOrgGuideline,
  updateOrgGuideline,
  deleteOrgGuideline,
  getOrgArticles,
  updateOrgArticle,
  deleteOrgArticle,
  updateOrgCode,
} from "../api/admin.js";

const TABS = [
  { id: "members", label: "회원 관리", icon: "users" },
  { id: "templates", label: "템플릿 관리", icon: "file-text" },
  { id: "guidelines", label: "작성 지침", icon: "clipboard-check" },
  { id: "articles", label: "기사 관리", icon: "newspaper" },
  { id: "settings", label: "조직 설정", icon: "settings" },
];

function getErrorMessage(error, fallback) {
  return error?.response?.data?.detail || error?.message || fallback;
}

function EmptyState({ title, description }) {
  return (
    <div className="admin-empty">
      <span className="admin-empty-mark">—</span>
      <strong>{title}</strong>
      <p>{description}</p>
    </div>
  );
}

function Modal({ title, onClose, children }) {
  return (
    <div
      className="admin-modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section className="admin-modal" role="dialog" aria-modal="true" aria-label={title}>
        <div className="admin-modal-heading">
          <h2>{title}</h2>
          <button className="admin-icon-button" type="button" onClick={onClose} aria-label="닫기">
            ×
          </button>
        </div>
        {children}
      </section>
    </div>
  );
}

function ResourceForm({ initialValue, resourceLabel, onCancel, onSubmit, saving }) {
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

function ResourceSection({ type, title, description, items, loading, onCreate, onEdit, onDelete }) {
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);
  const isGuideline = type === "guidelines";
  const label = isGuideline ? "작성 지침" : "템플릿";

  async function submit(data) {
    setSaving(true);
    try {
      if (editing?.id) await onEdit(editing.id, data);
      else await onCreate(data);
      setEditing(null);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="admin-content-section">
      <div className="admin-section-heading">
        <div>
          <p className="admin-eyebrow">ORGANIZATION WORKSPACE</p>
          <h1>{title}</h1>
          <p className="admin-section-description">{description}</p>
        </div>
        <button
          className="admin-button admin-button-primary"
          type="button"
          onClick={() => setEditing({})}
        >
          <span aria-hidden="true">＋</span> 새로 만들기
        </button>
      </div>
      {loading ? (
        <div className="admin-loading">불러오는 중...</div>
      ) : items.length ? (
        <div className="admin-resource-grid">
          {items.map((item) => (
            <article className="admin-resource-card" key={item.id}>
              <div className="admin-resource-card-top">
                <span className={`admin-resource-icon ${isGuideline ? "guideline" : "template"}`}>
                  {isGuideline ? "✓" : "▤"}
                </span>
                <div className="admin-resource-actions">
                  <button
                    className="admin-text-button"
                    type="button"
                    onClick={() => setEditing(item)}
                  >
                    수정
                  </button>
                  <button
                    className="admin-text-button danger"
                    type="button"
                    onClick={() => onDelete(item)}
                  >
                    삭제
                  </button>
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
          <ResourceForm
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

function MembersSection({ members, loading, onUpdate, onDelete, currentUser }) {
  const [editing, setEditing] = useState(null);
  const [nickname, setNickname] = useState("");
  const [role, setRole] = useState("member");
  const [saving, setSaving] = useState(false);

  function startEdit(member) {
    setEditing(member);
    setNickname(member.nickname || "");
    setRole(member.role || "member");
  }

  async function submit(event) {
    event.preventDefault();
    if (!nickname.trim()) return;
    setSaving(true);
    try {
      await onUpdate(editing.id, { nickname: nickname.trim(), role });
      setEditing(null);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="admin-content-section">
      <div className="admin-section-heading">
        <div>
          <p className="admin-eyebrow">ORGANIZATION WORKSPACE</p>
          <h1>회원 관리</h1>
          <p className="admin-section-description">조직 구성원의 계정 정보와 권한을 관리합니다.</p>
        </div>
        <span className="admin-count">{members.length}명</span>
      </div>
      <div className="admin-table-wrap">
        {loading ? (
          <div className="admin-loading">회원 목록을 불러오는 중...</div>
        ) : members.length ? (
          <table className="admin-table">
            <thead>
              <tr>
                <th>회원</th>
                <th>이메일</th>
                <th>권한</th>
                <th className="align-right">관리</th>
              </tr>
            </thead>
            <tbody>
              {members.map((member) => (
                <tr key={member.id}>
                  <td>
                    <div className="admin-member-cell">
                      <span className="admin-avatar">
                        {(member.nickname || member.email || "?").slice(0, 1).toUpperCase()}
                      </span>
                      <span>
                        <strong>{member.nickname || "이름 없음"}</strong>
                        {member.id === currentUser?.id && <small>내 계정</small>}
                      </span>
                    </div>
                  </td>
                  <td className="admin-muted">{member.email}</td>
                  <td>
                    <span
                      className={`admin-role-pill ${member.role === "admin" ? "is-admin" : ""}`}
                    >
                      {member.role === "admin" ? "관리자" : "일반 회원"}
                    </span>
                  </td>
                  <td className="align-right">
                    <button
                      className="admin-text-button"
                      type="button"
                      onClick={() => startEdit(member)}
                    >
                      수정
                    </button>
                    <button
                      className="admin-text-button danger"
                      type="button"
                      disabled={member.id === currentUser?.id}
                      onClick={() => onDelete(member)}
                    >
                      삭제
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <EmptyState
            title="회원이 없습니다"
            description="조직에 등록된 회원이 여기에 표시됩니다."
          />
        )}
      </div>
      {editing && (
        <Modal title="회원 정보 수정" onClose={() => setEditing(null)}>
          <form className="admin-form" onSubmit={submit}>
            <label>
              닉네임
              <input
                value={nickname}
                onChange={(event) => setNickname(event.target.value)}
                required
                maxLength={100}
              />
            </label>
            <label>
              권한
              <select value={role} onChange={(event) => setRole(event.target.value)}>
                <option value="member">일반 회원</option>
                <option value="admin">관리자</option>
              </select>
            </label>
            {editing.id === currentUser?.id && role !== currentUser?.role && (
              <p className="admin-inline-note">
                본인의 관리자 권한 변경은 서버에서 거부될 수 있습니다.
              </p>
            )}
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
                disabled={saving || !nickname.trim()}
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

function ArticlesSection({ articles, loading, onUpdate, onDelete }) {
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
      await onUpdate(editing.id, { title: title.trim(), visibility });
      setEditing(null);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="admin-content-section">
      <div className="admin-section-heading">
        <div>
          <p className="admin-eyebrow">ORGANIZATION WORKSPACE</p>
          <h1>기사 관리</h1>
          <p className="admin-section-description">
            조직에서 접근할 수 있는 기사를 확인하고 공개 범위를 관리합니다.
          </p>
        </div>
        <span className="admin-count">{articles.length}개</span>
      </div>
      <div className="admin-article-list">
        {loading ? (
          <div className="admin-loading">기사 목록을 불러오는 중...</div>
        ) : articles.length ? (
          articles.map((article) => (
            <article className="admin-article-row" key={article.id}>
              <div className="admin-article-symbol">▤</div>
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

function SettingsSection({ user, onRotateCode }) {
  const [confirmRotate, setConfirmRotate] = useState(false);
  const [rotating, setRotating] = useState(false);
  const [newCode, setNewCode] = useState("");

  async function rotate() {
    setRotating(true);
    try {
      const result = await onRotateCode();
      setNewCode(result?.code || result?.organization?.code || "");
      setConfirmRotate(false);
    } finally {
      setRotating(false);
    }
  }

  return (
    <section className="admin-content-section">
      <div className="admin-section-heading">
        <div>
          <p className="admin-eyebrow">ORGANIZATION WORKSPACE</p>
          <h1>조직 설정</h1>
          <p className="admin-section-description">조직 정보와 회원 초대 코드를 관리합니다.</p>
        </div>
      </div>
      <div className="admin-settings-card">
        <div>
          <span className="admin-settings-label">조직</span>
          <h2>{user?.organization_name || user?.organization?.name || "내 조직"}</h2>
          <p>조직의 템플릿과 작성 지침은 구성원들이 공통으로 사용할 수 있습니다.</p>
        </div>
        <div className="admin-settings-divider" />
        <div className="admin-code-row">
          <div>
            <span className="admin-settings-label">회원 초대 코드</span>
            <p>새로운 구성원이 가입할 때 사용하는 코드입니다.</p>
            {newCode && <strong className="admin-new-code">{newCode}</strong>}
          </div>
          <button
            className="admin-button admin-button-secondary"
            type="button"
            onClick={() => setConfirmRotate(true)}
          >
            코드 재발급
          </button>
        </div>
      </div>
      {confirmRotate && (
        <Modal title="초대 코드 재발급" onClose={() => setConfirmRotate(false)}>
          <div className="admin-confirm-body">
            <p>새 코드를 발급하면 이전 초대 코드는 더 이상 사용할 수 없습니다. 계속할까요?</p>
            <div className="admin-form-actions">
              <button
                className="admin-button admin-button-secondary"
                type="button"
                onClick={() => setConfirmRotate(false)}
              >
                취소
              </button>
              <button
                className="admin-button admin-button-primary"
                type="button"
                disabled={rotating}
                onClick={rotate}
              >
                {rotating ? "발급 중..." : "재발급"}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </section>
  );
}

export default function AdminPage({ user, onLogout, onBackToMain }) {
  const [activeTab, setActiveTab] = useState("members");
  const [members, setMembers] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [guidelines, setGuidelines] = useState([]);
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      if (activeTab === "members") setMembers(await getOrgMembers());
      else if (activeTab === "templates") setTemplates(await getOrgTemplates());
      else if (activeTab === "guidelines") setGuidelines(await getOrgGuidelines());
      else if (activeTab === "articles") setArticles(await getOrgArticles());
    } catch (err) {
      if (err?.response?.status === 401) {
        void onLogout?.();
        return;
      }
      setError(getErrorMessage(err, "데이터를 불러오지 못했습니다."));
    } finally {
      setLoading(false);
    }
  }, [activeTab, onLogout, reloadKey]);

  useEffect(() => {
    void load();
  }, [load]);

  async function perform(action, successMessage) {
    setError("");
    setNotice("");
    try {
      await action();
      setNotice(successMessage);
      setReloadKey((value) => value + 1);
    } catch (err) {
      setError(getErrorMessage(err, "요청을 처리하지 못했습니다."));
    }
  }

  async function removeMember(member) {
    if (member.id === user?.id) return;
    if (!window.confirm(`${member.nickname || member.email} 회원을 삭제할까요?`)) return;
    await perform(() => deleteOrgMember(member.id), "회원을 삭제했습니다.");
  }

  async function removeResource(kind, item) {
    if (!window.confirm(`'${item.title}' 항목을 삭제할까요?`)) return;
    const remove = kind === "templates" ? deleteOrgTemplate : deleteOrgGuideline;
    await perform(() => remove(item.id), "삭제했습니다.");
  }

  async function removeArticle(article) {
    if (!window.confirm(`'${article.title || "제목 없는 기사"}' 기사를 삭제할까요?`)) return;
    await perform(() => deleteOrgArticle(article.id), "기사를 삭제했습니다.");
  }

  async function rotateCode() {
    const result = await updateOrgCode();
    setNotice("초대 코드를 재발급했습니다.");
    return result;
  }

  const tabTitle = TABS.find((tab) => tab.id === activeTab)?.label || "관리자";

  return (
    <div className="admin-shell">
      <aside className="admin-sidebar">
        <button
          className="admin-brand"
          type="button"
          onClick={onBackToMain}
          aria-label="메인으로 이동"
        >
          <span className="admin-brand-mark">D</span>
          <span>
            deepbrief<small>WORKSPACE</small>
          </span>
        </button>
        <div className="admin-side-label">ADMINISTRATION</div>
        <nav className="admin-nav" aria-label="관리자 메뉴">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={`admin-nav-item ${activeTab === tab.id ? "active" : ""}`}
              onClick={() => {
                setActiveTab(tab.id);
                setError("");
                setNotice("");
              }}
            >
              <span className="admin-nav-icon" aria-hidden="true">
                {
                  {
                    users: "♙",
                    "file-text": "▤",
                    "clipboard-check": "✓",
                    newspaper: "▥",
                    settings: "⚙",
                  }[tab.icon]
                }
              </span>
              {tab.label}
              {activeTab === tab.id && <span className="admin-nav-active-mark" />}
            </button>
          ))}
        </nav>
        <div className="admin-sidebar-bottom">
          <UserProfile user={user} onLogout={onLogout} />
        </div>
      </aside>

      <main className="admin-main">
        <header className="admin-topbar">
          <div>
            <span>관리자</span>
            <span className="admin-breadcrumb-separator">/</span>
            <strong>{tabTitle}</strong>
          </div>
          <div className="admin-topbar-user">
            <span className="admin-status-dot" /> 관리자 모드
          </div>
        </header>
        <div className="admin-page-content">
          {error && (
            <div className="admin-feedback error" role="alert">
              <span>{error}</span>
              <button type="button" onClick={() => setReloadKey((value) => value + 1)}>
                다시 시도
              </button>
            </div>
          )}
          {notice && (
            <div className="admin-feedback success" role="status">
              <span>{notice}</span>
              <button type="button" onClick={() => setNotice("")}>
                닫기
              </button>
            </div>
          )}
          {activeTab === "members" && (
            <MembersSection
              members={members}
              loading={loading}
              currentUser={user}
              onUpdate={(id, data) =>
                perform(() => updateOrgMember(id, data), "회원 정보를 수정했습니다.")
              }
              onDelete={removeMember}
            />
          )}
          {activeTab === "templates" && (
            <ResourceSection
              type="templates"
              title="템플릿 관리"
              description="기사 작성 시 활용할 조직 공통 템플릿을 관리합니다."
              items={templates}
              loading={loading}
              onCreate={(data) => perform(() => createOrgTemplate(data), "템플릿을 만들었습니다.")}
              onEdit={(id, data) =>
                perform(() => updateOrgTemplate(id, data), "템플릿을 수정했습니다.")
              }
              onDelete={(item) => removeResource("templates", item)}
            />
          )}
          {activeTab === "guidelines" && (
            <ResourceSection
              type="guidelines"
              title="작성 지침 관리"
              description="기사 검토와 평가에 적용할 조직의 작성 기준을 관리합니다."
              items={guidelines}
              loading={loading}
              onCreate={(data) =>
                perform(() => createOrgGuideline(data), "작성 지침을 만들었습니다.")
              }
              onEdit={(id, data) =>
                perform(() => updateOrgGuideline(id, data), "작성 지침을 수정했습니다.")
              }
              onDelete={(item) => removeResource("guidelines", item)}
            />
          )}
          {activeTab === "articles" && (
            <ArticlesSection
              articles={articles}
              loading={loading}
              onUpdate={(id, data) =>
                perform(() => updateOrgArticle(id, data), "기사 정보를 수정했습니다.")
              }
              onDelete={removeArticle}
            />
          )}
          {activeTab === "settings" && <SettingsSection user={user} onRotateCode={rotateCode} />}
        </div>
        <footer className="admin-footer">
          deepbrief <span>·</span> 조직 관리
        </footer>
      </main>
    </div>
  );
}
