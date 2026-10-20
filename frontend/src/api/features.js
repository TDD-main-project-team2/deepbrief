import apiClient, { authConfig } from "./apiClient.js";
import { API_PATH } from "./config/paths.js";

export const askQuestion = async ({ conversationId, content }, accessToken) => {
  const body = { content };
  const response = await apiClient.post(
    API_PATH.features.qa(conversationId),
    body,
    authConfig(accessToken),
  );
  return response.data;
};

export const formatArticle = async ({ conversationId, templateId, content }, accessToken) => {
  const body = { content };
  const response = await apiClient.post(
    API_PATH.features.format(conversationId, templateId),
    body,
    authConfig(accessToken),
  );
  return response.data;
};

export const checkDuplicates = async ({ conversationId, content }, accessToken) => {
  const body = { content };
  const response = await apiClient.post(
    API_PATH.features.duplicate(conversationId),
    body,
    authConfig(accessToken),
  );
  return response.data;
};

export const evaluateArticle = async ({ conversationId, content }, accessToken) => {
  const body = { content };
  const response = await apiClient.post(
    API_PATH.features.evaluation(conversationId),
    body,
    authConfig(accessToken),
  );
  return response.data;
};

export const recommendTitle = async ({ conversationId, content }, accessToken) => {
  const body = { content };
  const response = await apiClient.post(
    API_PATH.features.title(conversationId),
    body,
    authConfig(accessToken),
  );
  return response.data;
};

export const recommendKeywords = async ({ conversationId, content }, accessToken) => {
  const body = { content };
  const response = await apiClient.post(
    API_PATH.features.keyword(conversationId),
    body,
    authConfig(accessToken),
  );
  return response.data;
};

export const recommendIdeas = async ({ conversationId, content }, accessToken) => {
  const body = { content };
  const response = await apiClient.post(
    API_PATH.features.ideas(conversationId),
    body,
    authConfig(accessToken),
  );
  return response.data;
};

export const getTemplateList = async (accessToken) => {
  const response = await apiClient.get(API_PATH.features.templates, authConfig(accessToken));
  return response.data;
};

export const extractHeadline = async ({ conversationId, content }, accessToken) => {
  const response = await apiClient.post(
    API_PATH.features.headline(conversationId),
    { content },
    authConfig(accessToken),
  );
  return response.data;
};
