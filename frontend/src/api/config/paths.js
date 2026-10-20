export const API_PATH = {
  auth: {
    register: "/auth/register",
    login: "/auth/login",
    refresh: "/auth/refresh",
    logout: "/auth/logout",
  },

  users: { me: "/users/me" },

  articles: {
    default: "/articles/",
    detail: (articleId) => `/articles/${articleId}`,
  },

  conversations: {
    default: "/conversations/",
    detail: (conversationId) => `/conversations/${conversationId}`,
    message: (messageId) => `/conversations/message/${messageId}`,
  },

  features: {
    qa: (conversationId) => `/features/conversations/${conversationId}/qa`,
    duplicate: (conversationId) =>
      `/features/conversations/${conversationId}/review/duplicate`,
    evaluation: (conversationId) =>
      `/features/conversations/${conversationId}/review/eval`,
    title: (conversationId) =>
      `/features/conversations/${conversationId}/recommend/title`,
    keyword: (conversationId) =>
      `/features/conversations/${conversationId}/recommend/keyword`,
    headline: (conversationId) =>
      `/features/conversations/${conversationId}/recommend/headline`,
    ideas: (conversationId) =>
      `/features/conversations/${conversationId}/recommend/ideas`,
    templates: "/features/templates",
    format: (conversationId, templateId) =>
      `/features/conversations/${conversationId}/format/${templateId}`,
  },

  health: "/health",
};
