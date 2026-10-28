// 서버의 기사를 화면용 데이터로 변환합니다. 원본 파일이 없으면 본문으로 TXT 미리보기를 만듭니다.
export function toArticleView(article, originalFile) {
  return {
    ...article,
    file: originalFile ?? new File([article.body], `${article.title}.txt`, { type: "text/plain" }),
    createdAt: article.created_at,
  };
}

// 서버의 대화 필드명을 화면에 맞추고, 역할별 메시지를 질문·답변 쌍으로 묶습니다.
export function toConversationView(conversation) {
  const messages = [];

  for (const message of conversation.messages ?? []) {
    if (message.role === "user") {
      messages.push({ question: message.content, answer: "" });
    } else if (message.role === "assistant") {
      const previous = messages.at(-1);
      if (previous && !previous.answer) previous.answer = message.content;
      else messages.push({ question: "", answer: message.content });
    }
  }

  return {
    ...conversation,
    articleId: conversation.article_id,
    createdAt: conversation.created_at,
    messages,
  };
}

// ID 기준으로 목록을 합치고, 중복 시 현재 데이터를 우선해 요청 중 추가된 업로드 기록을 보존합니다.
export function mergeHistory(loaded, current) {
  const items = new Map(loaded.map((item) => [item.id, item]));
  current.forEach((item) => items.set(item.id, item));
  return [...items.values()];
}
