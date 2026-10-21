import { useEffect, useState } from "react";

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
  const [query, setQuery] = useState({ tab: "members", version: 0 });
  const [completedQuery, setCompletedQuery] = useState(null);
  const activeTab = query.tab;
  const [members, setMembers] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [guidelines, setGuidelines] = useState([]);
  const [articles, setArticles] = useState([]);
  const loading = activeTab !== "settings" && completedQuery !== query;
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  function reload() {
    setError("");
    setQuery((current) => ({ ...current, version: current.version + 1 }));
  }

  useEffect(() => {
    let cancelled = false;
    const loaders = {
      members: { fetch: getOrgMembers, update: setMembers },
      templates: { fetch: getOrgTemplates, update: setTemplates },
      guidelines: { fetch: getOrgGuidelines, update: setGuidelines },
      articles: { fetch: getOrgArticles, update: setArticles },
    };
    const loader = loaders[query.tab];
    if (!loader) return;

    async function load() {
      try {
        const data = await loader.fetch();
        if (!cancelled) loader.update(data);
      } catch (err) {
        if (cancelled) return;
        if (err?.response?.status === 401) {
          void onLogout?.();
          return;
        }
        setError(getErrorMessage(err, "데이터를 불러오지 못했습니다."));
      } finally {
        if (!cancelled) setCompletedQuery(query);
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [query, onLogout]);

  async function perform(action, successMessage) {
    setError("");
    setNotice("");

    try {
      await action();
      setNotice(successMessage);
      reload();

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
            setQuery((current) =>
              current.tab === tab.id ? current : { tab: tab.id, version: current.version + 1 },
            );
            setError("");
            setNotice("");
          }}
        />
      </SidebarLayout>

      <main className="main admin-main">
        <div className="admin-page-content">
          <ErrorNotice onRetry={reload}>{error}</ErrorNotice>

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
