import { useRef, useState } from "react";

import "./MainPage.css";
import "../components/main/MainCommon.css";

import SideMenu from "../components/main/SideMenu.jsx";
import UploadForm from "../components/main/UploadForm.jsx";
import ArticlePanel from "../components/main/ArticlePanel.jsx";
import ChatPanel from "../components/main/ChatPanel.jsx";
import Archive from "../components/main/Archive.jsx";
import ArchivePreview from "../components/main/ArchivePreview.jsx";

import useFilePreview from "../hooks/useFilePreview.js";
import { createConversation } from "../api/conversations.js";
import { getArticle } from "../api/articles.js";
import { getAccessToken } from "../utils/tokenStorage.js";

export default function MainPage({ user, onLogout }) {
  const viewVersion = useRef(0); // 업로드를 기다리는 동안 사용자가 다른 화면으로 이동했는지 확인하는 값
  const pendingUploads = useRef(new WeakMap()); // 보통 같은 파일로 요청이 중복 실행되는 걸 막는 값

  const [uploadSession, setUploadSession] = useState(0);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [articleId, setArticleId] = useState(null);
  const [view, setView] = useState("chat");
  const [articles, setArticles] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [visibility, setVisibility] = useState("private");
  const [menuOpen, setMenuOpen] = useState(true);

  const { file, previewUrl, previewText, previewError, setPreviewError, changeFile } =
    useFilePreview();

  const activeConversation = conversations.find(
    (conversation) => conversation.id === activeConversationId,
  );
  const hasActiveConversation = Boolean(activeConversation);
  const messages = activeConversation?.messages || [];

  function sendMessage(messageText) {
    if (!messageText.trim() || !activeConversation) return;

    const message = {
      question: messageText,
      answer: `“${messageText}” 요청을 받았습니다.\n\n@@@@ 여기에 결과 넣기 @@@@`,
    };

    setConversations((conversations) =>
      conversations.map((conversation) =>
        conversation.id === activeConversationId
          ? { ...conversation, messages: [...conversation.messages, message] }
          : conversation,
      ),
    );
  }

  function openChat(conversation) {
    viewVersion.current += 1;
    const article = articles.find((article) => article.id === conversation.articleId);

    if (!article) return;

    setActiveConversationId(conversation.id);
    changeFile(article.file);
    setVisibility(article.visibility);
    setView("chat");
  }

  function openArticle(article) {
    viewVersion.current += 1;
    setArticleId(article.id);
    changeFile(article.file);
    setVisibility(article.visibility);
    setView("article");
  }

  async function startConversationWithFile({ file: uploadedFile, visibility: uploadedVisibility }) {
    const token = getAccessToken();
    const version = viewVersion.current;

    try {
      // 기사 조회만 실패했다면 이미 생성한 대화를 다시 사용합니다.
      let result = pendingUploads.current.get(uploadedFile);

      if (!result) {
        result = await createConversation({
          file: uploadedFile,
          title: uploadedFile.name.trim().slice(0, 255),
          visibility: uploadedVisibility,
        });
        pendingUploads.current.set(uploadedFile, result);
      }

      const articleData = await getArticle({ articleId: result.article_id });

      if (getAccessToken() !== token) return;
      pendingUploads.current.delete(uploadedFile);

      const article = {
        ...articleData,
        file: uploadedFile,
        createdAt: articleData.created_at,
      };

      const conversation = {
        ...result,
        articleId: result.article_id,
        createdAt: result.created_at,
      };

      setArticles((items) => [...items.filter((item) => item.id !== article.id), article]);
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
      if (error.response?.status === 401 && getAccessToken() === token) {
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
      if (deletesOpenArticle) setView(article.visibility);
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
  };

  return (
    <div className={`shell ${menuOpen ? "menu-open" : "menu-closed"}`}>
      <SideMenu {...sideMenuProps} />

      <div className="main">
        {view === "article" && (
          <main className="article-detail-main split-main">
            <ArchivePreview
              {...previewProps}
              articles={articles}
              articleId={articleId}
              setView={changeView}
            />
          </main>
        )}

        {(view === "private" || view === "public") && (
          <main className="archive-main">
            <Archive
              view={view}
              articles={articles}
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
