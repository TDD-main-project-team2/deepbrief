import { useCallback, useEffect, useState } from "react";

import "./AdminPage.css";

import CompletionNotice from "../components/common/feedback/CompletionNotice.jsx";
import ErrorNotice from "../components/common/feedback/ErrorNotice.jsx";
import MembersContent from "../components/admin/MembersContent.jsx";
import TemplatesContent from "../components/admin/TemplatesContent.jsx";
import GuidelinesContent from "../components/admin/GuidelinesContent.jsx";
import ArticlesContent from "../components/admin/ArticlesContent.jsx";
import OrganizationContent from "../components/admin/OrganizationContent.jsx";
import MenuContent from "../components/admin/MenuContent.jsx";
import SidebarLayout from "../components/common/side-menu/SidebarLayout.jsx";
import { getOrgMembers, getOrgTemplates, getOrgGuidelines, getOrgArticles } from "../api/admin.js";

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

  return (
    <div className={`shell admin-shell ${menuOpen ? "menu-open" : "menu-closed"}`}>
      <CompletionNotice message={notice} onClose={() => setNotice("")} />

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
              onPerform={perform}
            />
          )}
          {activeTab === "templates" && (
            <TemplatesContent items={templates} loading={loading} onPerform={perform} />
          )}
          {activeTab === "guidelines" && (
            <GuidelinesContent items={guidelines} loading={loading} onPerform={perform} />
          )}
          {activeTab === "articles" && (
            <ArticlesContent articles={articles} loading={loading} onPerform={perform} />
          )}
          {activeTab === "settings" && <OrganizationContent user={user} onComplete={setNotice} />}
        </div>
      </main>
    </div>
  );
}
