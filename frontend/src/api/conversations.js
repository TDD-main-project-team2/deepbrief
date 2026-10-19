import apiClient, { authConfig } from "./apiClient.js";
import { API_PATH } from "./config/paths.js";

export const getConversations = async (accessToken) => {
  const response = await apiClient.get(API_PATH.conversations.default, authConfig(accessToken));
  return response.data;
};

export const getConversation = async ({ conversationId }, accessToken) => {
  const response = await apiClient.get(
    API_PATH.conversations.detail(conversationId),
    authConfig(accessToken),
  );
  return response.data;
};

export const deleteConversation = async ({ conversationId }, accessToken) => {
  await apiClient.delete(API_PATH.conversations.detail(conversationId), authConfig(accessToken));
};

export const createConversation = async ({ file, title }, accessToken) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("title", title);

  const response = await apiClient.post(
    API_PATH.conversations.default,
    formData,
    authConfig(accessToken),
  );
  return response.data;
};

export const deleteMessage = async ({ messageId }, accessToken) => {
  await apiClient.delete(API_PATH.conversations.message(messageId), authConfig(accessToken));
};
