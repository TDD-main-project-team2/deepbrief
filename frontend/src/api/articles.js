import apiClient, { authConfig } from "./apiClient.js";
import { API_PATH } from "./config/paths.js";

export const getArticleList = async (accessToken) => {
  const response = await apiClient.get(API_PATH.articles.default, authConfig(accessToken));
  return response.data;
};

export const getPublicArticleList = async (accessToken) => {
  const response = await apiClient.get(API_PATH.articles.public, authConfig(accessToken));
  return response.data;
};

export const getArticle = async ({ articleId }, accessToken) => {
  const response = await apiClient.get(
    API_PATH.articles.detail(articleId),
    authConfig(accessToken),
  );
  return response.data;
};

export const deleteArticle = async ({ articleId }, accessToken) => {
  await apiClient.delete(API_PATH.articles.detail(articleId), authConfig(accessToken));
};
