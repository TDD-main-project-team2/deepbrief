import apiClient from "./apiClient.js";
import { API_PATH } from "./config/paths.js";

// Members
export const getOrgMembers = async () => {
  const response = await apiClient.get(API_PATH.admin.members);
  return response.data || [];
};

export const updateOrgMember = async (memberId, data) => {
  const response = await apiClient.patch(API_PATH.admin.member(memberId), data);
  return response.data;
};

export const deleteOrgMember = async (memberId) => {
  await apiClient.delete(API_PATH.admin.member(memberId));
};

// Templates
export const getOrgTemplates = async () => {
  const response = await apiClient.get(API_PATH.admin.templates);
  return response.data || [];
};

export const createOrgTemplate = async (data) => {
  const response = await apiClient.post(API_PATH.admin.templates, data);
  return response.data;
};

export const updateOrgTemplate = async (templateId, data) => {
  const response = await apiClient.patch(API_PATH.admin.template(templateId), data);
  return response.data;
};

export const deleteOrgTemplate = async (templateId) => {
  await apiClient.delete(API_PATH.admin.template(templateId));
};

// Guidelines
export const getOrgGuidelines = async () => {
  const response = await apiClient.get(API_PATH.admin.guidelines);
  return response.data || [];
};

export const createOrgGuideline = async (data) => {
  const response = await apiClient.post(API_PATH.admin.guidelines, data);
  return response.data;
};

export const updateOrgGuideline = async (guidelineId, data) => {
  const response = await apiClient.patch(API_PATH.admin.guideline(guidelineId), data);
  return response.data;
};

export const deleteOrgGuideline = async (guidelineId) => {
  await apiClient.delete(API_PATH.admin.guideline(guidelineId));
};

// Articles
export const getOrgArticles = async () => {
  const response = await apiClient.get(API_PATH.admin.articles);
  return response.data?.articles || [];
};

export const updateOrgArticle = async (articleId, data) => {
  const response = await apiClient.patch(API_PATH.admin.article(articleId), data);
  return response.data;
};

export const deleteOrgArticle = async (articleId) => {
  await apiClient.delete(API_PATH.admin.article(articleId));
};

// Organization code
export const updateOrgCode = async () => {
  const response = await apiClient.patch(API_PATH.admin.code);
  return response.data;
};