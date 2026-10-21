import { useCallback, useEffect, useState } from "react";

import "./AdminPage.css";

import CompletionNotice from "../components/common/feedback/CompletionNotice.jsx";
import ErrorNotice from "../components/common/feedback/ErrorNotice.jsx";
import MembersContent from "../components/admin/MembersContent.jsx";
import TemplatesContent from "../components/admin/TemplatesContent.jsx";
import GuidelinesContent from "../components/admin/GuidelinesContent.jsx";
import ArticlesContent from "../components/admin/ArticlesContent.jsx";
import SettingsContent from "../components/admin/SettingsContent.jsx";
import MenuContent from "../components/admin/MenuContent.jsx";
import SidebarLayout from "../components/common/side-menu/SidebarLayout.jsx";
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

function getErrorMessage(error, fallback) {
  return error?.response?.data?.detail || error?.message || fallback;
}

export default function AdminPage({ user, onLogout, onBackToMain }) {
  const [menuOpen, setMenuOpen] = useState(true);
  const [activeTab, setActiveTab] = useState("members");
  const [members, setMembers] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [guidelines, setGuidelines] = useState([]);
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [confirmation, setConfirmation] = useState(null);
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
      return true;
    } catch (err) {
      setError(getErrorMessage(err, "요청을 처리하지 못했습니다."));
      return false;
    }
  }

  function removeMember(member) {
    if (member.id === user?.id) return;
    setConfirmation({
      title: "회원을 삭제할까요?",
      message: `${member.nickname || member.email} 회원을 삭제합니다.`,
      action: () => deleteOrgMember(member.id),
      successMessage: "회원을 삭제했습니다.",
    });
  }

  function removeResource(kind, item) {
    const remove = kind === "templates" ? deleteOrgTemplate : deleteOrgGuideline;
    setConfirmation({
      title: "항목을 삭제할까요?",
      message: `'${item.title}' 항목을 삭제합니다.`,
      action: () => remove(item.id),
      successMessage: "삭제했습니다.",
    });
  }

  function removeArticle(article) {
    setConfirmation({
      title: "기사를 삭제할까요?",
      message: `'${article.title || "제목 없는 기사"}' 기사를 삭제합니다.`,
      action: () => deleteOrgArticle(article.id),
      successMessage: "기사를 삭제했습니다.",
    });
  }

  async function rotateCode() {
    const result = await updateOrgCode();
    setNotice("초대 코드를 재발급했습니다.");
    return result;
  }

  return (
    <div className={`shell admin-shell ${menuOpen ? "menu-open" : "menu-closed"}`}>
      <CompletionNotice message={notice} onClose={() => setNotice("")} />
      <CompletionNotice
        title={confirmation?.title}
        message={confirmation?.message}
        onClose={() => setConfirmation(null)}
        onConfirm={() => {
          if (!confirmation) return;
          const { action, successMessage } = confirmation;
          setConfirmation(null);
          void perform(action, successMessage);
        }}
        confirmLabel="삭제"
      />
      <SidebarLayout
        id="admin-menu"
        menuOpen={menuOpen}
        onToggle={() => setMenuOpen((open) => !open)}
        user={user}
        onLogout={onLogout}
        onHeaderClick={onBackToMain}
      >
        <MenuContent
          activeTab={activeTab}
          onSelect={(tab) => {
            setActiveTab(tab.id);
            setError("");
            setNotice("");
          }}
        />
      </SidebarLayout>

      <main className="main admin-main">
        <div className="admin-page-content">
          <ErrorNotice onRetry={() => setReloadKey((value) => value + 1)}>{error}</ErrorNotice>

          {activeTab === "members" && (
            <MembersContent
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
            <TemplatesContent
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
            <GuidelinesContent
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
            <ArticlesContent
              articles={articles}
              loading={loading}
              onUpdate={(id, data) =>
                perform(() => updateOrgArticle(id, data), "기사 정보를 수정했습니다.")
              }
              onDelete={removeArticle}
            />
          )}

          {activeTab === "settings" && <SettingsContent user={user} onRotateCode={rotateCode} />}
        </div>
      </main>
    </div>
  );
}
