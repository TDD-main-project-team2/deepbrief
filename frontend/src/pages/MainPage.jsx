import { useState } from "react";

import "./MainPage.css";
import "../components/main/MainCommon.css";

import SideMenu from "../components/main/SideMenu.jsx";
import UploadForm from "../components/main/UploadForm.jsx";
import ArticlePanel from "../components/main/ArticlePanel.jsx";
import ChatPanel from "../components/main/ChatPanel.jsx";
import Archive from "../components/main/Archive.jsx";
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
    const article = articles.find((article) => article.id === conversation.articleId);

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

  function startConversationWithFile({ file: uploadedFile, visibility: uploadedVisibility }) {
    // 저장 API 연결 전, 브라우저 시안의 기록 선택에만 쓰는 임시 ID입니다.
    // API 연결 시 아래 레코드를 서버가 반환한 article/conversation으로 대체합니다.
    const localArticleId = `local-article-${crypto.randomUUID()}`;
    const localConversationId = `local-conversation-${crypto.randomUUID()}`;
    const article = {
      id: localArticleId,
      file: uploadedFile,
      visibility: uploadedVisibility,
      category: null,
    };
    const conversation = {
      id: localConversationId,
      articleId: localArticleId,
      messages: [],
    };

    setArticles((articles) => [...articles, article]);
    setConversations((conversations) => [...conversations, conversation]);
    setActiveConversationId(conversation.id);
    changeFile(article.file);
    setVisibility(article.visibility);
    setView("chat");
  }

  function startNewConversation() {
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
        onStartNewConversation={startNewConversation}
        articles={articles}
        view={view}
        activeConversationId={activeConversationId}
        conversations={conversations}
        openChat={openChat}
        onDeleteConversation={deleteConversation}
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
