import { useState } from "react";

import "./MainPage.css";
import "../components/main/MainCommon.css";

import SideMenu from "../components/main/SideMenu.jsx";
import UploadForm from "../components/main/UploadForm.jsx";
import ArticlePanel from "../components/main/ArticlePanel.jsx";
import ChatPanel from "../components/main/ChatPanel.jsx";
import ArticleArchive from "../components/main/ArticleArchive.jsx";
import ArchivePreview from "../components/main/ArchivePreview.jsx";

import useFilePreview from "../hooks/useFilePreview.js";

export default function MainPage({ user, onLogout }) {
  const [uploadSession, setUploadSession] = useState(0);
  const [activeConversationId, setActiveConversationId] = useState(null),
    [articleId, setArticleId] = useState(null),
    [view, setView] = useState("chat"),
    [articles, setArticles] = useState([]),
    [conversations, setConversations] = useState([]),
    [visibility, setVisibility] = useState("private"),
    [menuOpen, setMenuOpen] = useState(true);

  const {
    file,
    previewUrl,
    previewText,
    previewError,
    setPreviewError,
    changeFile,
  } = useFilePreview();

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
    const article = articles.find(
      (article) => article.id === conversation.articleId,
    );

    if (!article) return;

    setActiveConversationId(conversation.id);
    changeFile(article.file);
    setVisibility(article.visibility);
    setView("chat");
  }

  function openArticle(article) {
    setArticleId(article.id);
    changeFile(article.file);
    setVisibility(article.visibility);
    setView("article");
  }

  function createConversation({
    file: uploadedFile,
    visibility: uploadedVisibility,
  }) {
    const articleId = crypto.randomUUID();
    const conversationId = crypto.randomUUID();
    const createdAt = new Date().toISOString();

    const article = {
      id: articleId,
      file: uploadedFile,
      visibility: uploadedVisibility,
      category: null,
      createdAt,
    };
    const conversation = {
      id: conversationId,
      articleId,
      createdAt,
      messages: [],
    };

    setArticles((articles) => [...articles, article]);
    setConversations((conversations) => [...conversations, conversation]);
    setActiveConversationId(conversationId);
    changeFile(uploadedFile);
    setVisibility(uploadedVisibility);
    setView("chat");
  }

  function openUploadForm() {
    setActiveConversationId(null);
    setArticleId(null);
    setView("chat");
    setVisibility("private");
    changeFile(null);
    setUploadSession((session) => session + 1);
  }

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
      <SideMenu
        menuOpen={menuOpen}
        setMenuOpen={setMenuOpen}
        onOpenUploadForm={openUploadForm}
        articles={articles}
        view={view}
        activeConversationId={activeConversationId}
        conversations={conversations}
        openChat={openChat}
        setView={setView}
        user={user}
        onLogout={onLogout}
      />

      <div className="main">
        {view === "article" && (
          <main className="article-detail-main split-main">
            <ArchivePreview
              {...previewProps}
              articles={articles}
              articleId={articleId}
              setView={setView}
            />
          </main>
        )}
        {(view === "private" || view === "public") && (
          <main className="archive-main">
            <ArticleArchive
              view={view}
              articles={articles}
              openArticle={openArticle}
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
                onCreateConversation={createConversation}
              />
            </main>
          ))}
      </div>
    </div>
  );
}
