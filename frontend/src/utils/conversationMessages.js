// 요청을 보낼 때 해당 대화에 질문과 로딩 상태를 담은 메시지를 추가합니다.
export function appendConversationMessage(conversations, conversationId, message) {
  return conversations.map((conversation) =>
    conversation.id === conversationId
      ? { ...conversation, messages: [...conversation.messages, message] }
      : conversation,
  );
}

// API 응답 후 메시지에 답변 또는 오류를 반영합니다.
export function updateConversationMessage(conversations, conversationId, requestId, changes) {
  return conversations.map((conversation) =>
    conversation.id === conversationId
      ? {
          ...conversation,
          messages: conversation.messages.map((message) =>
            message.requestId === requestId ? { ...message, ...changes } : message,
          ),
        }
      : conversation,
  );
}
