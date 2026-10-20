import { useEffect, useRef, useState } from "react";

import "./MainPage.css";
import "../components/main/MainCommon.css";

import SideMenu from "../components/main/SideMenu.jsx";
import UploadForm from "../components/main/UploadForm.jsx";
import ArticlePanel from "../components/main/ArticlePanel.jsx";
import ChatPanel from "../components/main/ChatPanel.jsx";
import Archive from "../components/main/Archive.jsx";
import ArchivePreview from "../components/main/ArchivePreview.jsx";
import ErrorNotice from "../components/ErrorNotice.jsx";
import LoadingNotice from "../components/LoadingNotice.jsx";

import useFilePreview from "../hooks/useFilePreview.js";
import useConversationWithFile from "../hooks/useConversationWithFile.js";
import useConversationMessages from "../hooks/useConversationMessages.js";

import { getConversationList, getConversation } from "../api/conversations.js";
import { getArticle, getArticleList, getPublicArticleList } from "../api/articles.js";
import { getAuthSessionVersion } from "../utils/tokenStorage.js";
import { toArticleView, toConversationView, mergeHistory } from "../utils/historyDataAdapters.js";

export default function MainPage({ user, onLogout }) {
  const viewVersion = useRef(0); // 업로드를 기다리는 동안 사용자가 다른 화면으로 이동했는지 확인하는 값
  const createConversationWithFile = useConversationWithFile();

  const [uploadSession, setUploadSession] = useState(0);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [articleId, setArticleId] = useState(null);
  const [view, setView] = useState("chat");
  const [archiveView, setArchiveView] = useState("private");
  const [articles, setArticles] = useState([]);
  const [publicArticles, setPublicArticles] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [visibility, setVisibility] = useState("private");
  const [menuOpen, setMenuOpen] = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [historyError, setHistoryError] = useState("");
  const [historyReload, setHistoryReload] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const requestSessionVersion = getAuthSessionVersion();

    async function loadHistory() {
      try {
        const [articleResult, conversationResult, publicResult] = await Promise.all([
          getArticleList(),
          getConversationList(),
          getPublicArticleList(),
        ]);

        if (cancelled || getAuthSessionVersion() !== requestSessionVersion) return;

        setArticles((current) =>
          mergeHistory(
            articleResult.articles.map((item) => toArticleView(item)),
            current,
          ),
        );
        setPublicArticles(publicResult.articles.map((item) => toArticleView(item)));
        setConversations((current) =>
          mergeHistory(conversationResult.map(toConversationView), current),
        );
      } catch (error) {
        if (cancelled || getAuthSessionVersion() !== requestSessionVersion) return;
        if (error.response?.status === 401) void onLogout();
        else setHistoryError("기사·대화 목록을 불러오지 못했습니다. 다시 시도해주세요.");
      } finally {
        if (!cancelled) setLoadingHistory(false);
      }
    }

    loadHistory();

    return () => {
      cancelled = true;
    };
  }, [user?.id, onLogout, historyReload]);

  function retryHistory() {
    setHistoryError("");
    setLoadingHistory(true);
    setHistoryReload((value) => value + 1);
  }

  const { file, previewUrl, previewText, previewError, setPreviewError, changeFile } =
    useFilePreview();

  const activeConversation = conversations.find(
    (conversation) => conversation.id === activeConversationId,
  );
  const hasActiveConversation = Boolean(activeConversation);
  const messages = activeConversation?.messages || [];

  const { sendMessage, isConversationPending } = useConversationMessages({
    activeConversation,
    setConversations,
    onLogout,
  });

  async function openChat(conversation) {
    const messagesBeforeLoad = conversation.messages;
    const version = ++viewVersion.current;
    const requestSessionVersion = getAuthSessionVersion();

    setHistoryError("");

    try {
      const detail = await getConversation({ conversationId: conversation.id });
      const cachedArticle = articles.find((article) => article.id === detail.article_id);
      const article =
        cachedArticle ?? toArticleView(await getArticle({ articleId: detail.article_id }));

      if (version !== viewVersion.current || getAuthSessionVersion() !== requestSessionVersion)
        return;
      if (!cachedArticle) setArticles((items) => mergeHistory(items, [article]));

      const restored = toConversationView(detail);

      setConversations((items) =>
        items.map((item) =>
          item.id === restored.id
            ? isConversationPending(item.id) || item.messages !== messagesBeforeLoad
              ? { ...restored, messages: item.messages }
              : restored
            : item,
        ),
      );
      setActiveConversationId(restored.id);
      changeFile(article.file);
      setVisibility(article.visibility);
      setView("chat");
    } catch (error) {
      if (version !== viewVersion.current || getAuthSessionVersion() !== requestSessionVersion)
        return;
      if (error.response?.status === 401) void onLogout();
      else setHistoryError("대화를 불러오지 못했습니다. 대화를 다시 선택해주세요.");
    }
  }

  function openArticle(article) {
    viewVersion.current += 1;
    setArchiveView(view === "public" ? "public" : "private");
    setArticleId(article.id);
    changeFile(article.file);
    setVisibility(article.visibility);
    setView("article");
  }

  async function startConversationWithFile({ file: uploadedFile, visibility: uploadedVisibility }) {
    const requestSessionVersion = getAuthSessionVersion();
    const version = viewVersion.current;

    try {
      const result = await createConversationWithFile({
        file: uploadedFile,
        visibility: uploadedVisibility,
      });
      if (!result) return;

      const { article, conversation } = result;

      setArticles((items) => [...items.filter((item) => item.id !== article.id), article]);
      if (article.visibility === "public") {
        setPublicArticles((items) => mergeHistory(items, [article]));
      }
      setConversations((items) => [
        ...items.filter((item) => item.id !== conversation.id),
        conversation,
      ]);

      if (viewVersion.current !== version) return;

      setActiveConversationId(conversation.id);
      changeFile(article.file);
      setVisibility(article.visibility);
      setView("chat");
    } catch (error) {
      if (error.response?.status === 401 && getAuthSessionVersion() === requestSessionVersion) {
        void onLogout();
        return;
      }
      throw error;
    }
  }

  function startNewConversation() {
    viewVersion.current += 1;
    setActiveConversationId(null);
    setArticleId(null);
    setView("chat");
    setVisibility("private");
    changeFile(null);
    setUploadSession((session) => session + 1);
  }

  function deleteConversation(conversation) {
    if (!window.confirm("이 대화를 삭제할까요? 기사 파일은 보관함에 유지됩니다.")) return;

    setConversations((conversations) =>
      conversations.filter((existingConversation) => existingConversation.id !== conversation.id),
    );

    if (activeConversationId === conversation.id) {
      if (view === "chat") startNewConversation();
      else setActiveConversationId(null);
    }
  }

  function deleteArticle(article) {
    if (!window.confirm("이 기사를 삭제할까요? 연결된 대화 기록도 함께 삭제됩니다.")) return;

    const deletesActiveConversation = activeConversation?.articleId === article.id;
    const deletesOpenArticle = view === "article" && articleId === article.id;

    setArticles((articles) =>
      articles.filter((existingArticle) => existingArticle.id !== article.id),
    );
    setConversations((conversations) =>
      conversations.filter((conversation) => conversation.articleId !== article.id),
    );

    if (deletesOpenArticle || (view === "chat" && deletesActiveConversation)) {
      startNewConversation();
      if (deletesOpenArticle) setView(archiveView);
    } else {
      if (deletesActiveConversation) setActiveConversationId(null);
      if (articleId === article.id) setArticleId(null);
    }
  }

  function changeView(nextView) {
    viewVersion.current += 1;
    setView(nextView);
  }

  const sideMenuProps = {
    menuOpen,
    setMenuOpen,
    onStartNewConversation: startNewConversation,
    articles,
    publicArticleCount: publicArticles.length,
    view,
    activeConversationId,
    conversations,
    openChat,
    onDeleteConversation: deleteConversation,
    setView: changeView,
    user,
    onLogout,
  };

  const previewProps = {
    file,
    visibility,
    previewUrl,
    previewText,
    previewError,
    setPreviewError,
    article: (view === "article" && archiveView === "public" ? publicArticles : articles).find(
      (article) => article.id === (view === "article" ? articleId : activeConversation?.articleId),
    ),
  };

  return (
    <div className={`shell ${menuOpen ? "menu-open" : "menu-closed"}`}>
      <SideMenu {...sideMenuProps} />

      <div className="main">
        {loadingHistory && !historyError && (
          <LoadingNotice className="history-feedback">목록을 불러오는 중...</LoadingNotice>
        )}

        <ErrorNotice
          className="history-feedback"
          onRetry={retryHistory}
          retryLabel="목록 다시 불러오기"
        >
          {historyError}
        </ErrorNotice>

        {view === "article" && (
          <main className="article-detail-main split-main">
            <ArchivePreview {...previewProps} archiveView={archiveView} setView={changeView} />
          </main>
        )}

        {(view === "private" || view === "public") && (
          <main className="archive-main">
            <Archive
              view={view}
              articles={view === "public" ? publicArticles : articles}
              openArticle={openArticle}
              onDeleteArticle={deleteArticle}
            />
          </main>
        )}

        {view === "chat" &&
          (hasActiveConversation ? (
            <main className="split-main">
              <ArticlePanel {...previewProps} />
              <ChatPanel
                key={activeConversationId}
                messages={messages}
                isSending={messages.some((message) => message.pending)}
                onSendMessage={sendMessage}
              />
            </main>
          ) : (
            <main className="welcome-main">
              <UploadForm
                key={uploadSession}
                onStartConversationWithFile={startConversationWithFile}
              />
            </main>
          ))}
      </div>
    </div>
  );
}
