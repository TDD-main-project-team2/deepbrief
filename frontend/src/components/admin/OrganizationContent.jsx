import { updateOrgCode } from "../../api/admin.js";
import { useState } from "react";

import "./AdminCommon.css";
import "./OrganizationContent.css";

import ContentHeader from "../common/ContentHeader.jsx";
import CompletionNotice from "../common/feedback/CompletionNotice.jsx";
import ErrorNotice from "../common/feedback/ErrorNotice.jsx";

export default function OrganizationContent({ user, onComplete }) {
  const [confirmRotate, setConfirmRotate] = useState(false);
  const [error, setError] = useState("");
  const [rotating, setRotating] = useState(false);
  const [newCode, setNewCode] = useState("");

  async function rotate() {
    setConfirmRotate(false);
    setError("");
    setRotating(true);
    try {
      const result = await updateOrgCode();
      setNewCode(result?.code || result?.organization?.code || "");
      onComplete("초대 코드를 재발급했습니다.");
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || "초대 코드를 재발급하지 못했습니다.");
    } finally {
      setRotating(false);
    }
  }

  return (
    <section className="admin-content-section">
      <ContentHeader
        caption="ORGANIZATION SETTINGS"
        title="조직 설정"
        description="조직 정보와 회원 초대 코드를 관리합니다."
      />

      <ErrorNotice>{error}</ErrorNotice>

      <div className="admin-settings-card">
        <div>
          <h2>{user?.organization_name || "소속 조직 정보 없음"}</h2>
          <p>조직의 템플릿과 작성 지침은 구성원들이 공통으로 사용할 수 있습니다.</p>
        </div>
        <div className="admin-settings-divider" />
        <div className="admin-code-row">
          <div>
            <span className="admin-code-label">회원 초대 코드</span>
            <p>새로운 구성원이 가입할 때 사용하는 코드입니다.</p>
            {newCode && <strong className="admin-new-code">{newCode}</strong>}
          </div>
          <button
            className="admin-button admin-button-secondary"
            type="button"
            disabled={rotating}
            onClick={() => setConfirmRotate(true)}
          >
            {rotating ? "발급 중..." : "코드 재발급"}
          </button>
        </div>
      </div>

      <CompletionNotice
        title="초대 코드를 재발급할까요?"
        message={
          confirmRotate ? "새 코드를 발급하면 이전 초대 코드는 더 이상 사용할 수 없습니다." : ""
        }
        onClose={() => setConfirmRotate(false)}
        onConfirm={rotate}
        confirmLabel="재발급"
      />
    </section>
  );
}
