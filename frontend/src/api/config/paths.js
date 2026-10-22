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
    public: "/articles/public",
    detail: (articleId) => `/articles/${articleId}`,
  },

  conversations: {
    default: "/conversations/",
    detail: (conversationId) => `/conversations/${conversationId}`,
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

  admin: {
    members: "/admin/members",
    member: (memberId) => `/admin/members/${memberId}`,

    templates: "/admin/templates",
    template: (templateId) => `/admin/templates/${templateId}`,

    guidelines: "/admin/guidelines",
    guideline: (guidelineId) => `/admin/guidelines/${guidelineId}`,

    articles: "/admin/articles",
    article: (articleId) => `/admin/articles/${articleId}`,

    code: "/admin/code",
  },
};
