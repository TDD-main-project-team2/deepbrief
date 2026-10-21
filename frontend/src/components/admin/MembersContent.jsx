import { updateOrgMember, deleteOrgMember } from "../../api/admin.js";
import CompletionNotice from "../common/feedback/CompletionNotice.jsx";
import { useState } from "react";

import "./AdminCommon.css";
import "./MembersContent.css";

import ContentHeader from "../common/ContentHeader.jsx";
import EditButton from "../common/buttons/EditButton.jsx";
import DeleteButton from "../common/buttons/DeleteButton.jsx";
import EmptyState from "./EmptyState.jsx";
import Modal from "./Modal.jsx";

export default function MembersContent({ members, loading, onPerform, currentUser }) {
  const [deleting, setDeleting] = useState(null);
  const [editing, setEditing] = useState(null);
  const [nickname, setNickname] = useState("");
  const [role, setRole] = useState("member");
  const [saving, setSaving] = useState(false);

  function startEdit(member) {
    setEditing(member);
    setNickname(member.nickname || "");
    setRole(member.role || "member");
  }

  function removeMember(member) {
    if (member.id === currentUser?.id) return;
    setDeleting(member);
  }

  async function submit(event) {
    event.preventDefault();
    if (!nickname.trim()) return;
    setSaving(true);
    try {
      const saved = await onPerform(
        () => updateOrgMember(editing.id, { nickname: nickname.trim(), role }),
        "회원 정보를 수정했습니다.",
      );
      if (saved !== false) setEditing(null);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="admin-content-section">
      <CompletionNotice
        title="회원을 삭제할까요?"
        message={deleting ? `${deleting.nickname || deleting.email} 회원을 삭제합니다.` : ""}
        onClose={() => setDeleting(null)}
        onConfirm={() => {
          if (!deleting) return;
          const id = deleting.id;
          setDeleting(null);
          void onPerform(() => deleteOrgMember(id), "회원을 삭제했습니다.");
        }}
        confirmLabel="삭제"
      />

      <ContentHeader
        caption="MEMBER MANAGEMENT"
        title="회원 관리"
        description="조직 구성원의 계정 정보와 권한을 관리합니다."
        actions={<strong className="members-count">{members.length}명의 사용자</strong>}
      />

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
                <th>관리</th>
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
                  <td className="admin-member-actions">
                    <EditButton
                      label={`${member.nickname || member.email} 회원 수정`}
                      onClick={() => startEdit(member)}
                    />
                    <DeleteButton
                      label={`${member.nickname || member.email} 회원 삭제`}
                      disabled={member.id === currentUser?.id}
                      onClick={() => removeMember(member)}
                    />
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
