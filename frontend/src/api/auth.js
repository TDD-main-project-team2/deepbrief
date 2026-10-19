import apiClient from "./apiClient.js";
import { API_PATH } from "./config/paths.js";

export const signupUser = async ({ email, password, nickname, organizationCode }) => {
  const body = { email, password, nickname, organization_code: organizationCode };
  const response = await apiClient.post(API_PATH.auth.register, body);
  return response.data;
};

export const loginUser = async ({ email, password }) => {
  const body = { email, password };
  const response = await apiClient.post(API_PATH.auth.login, body);
  return response.data;
};

export const refreshTokens = async ({ refreshToken }) => {
  const body = { refresh_token: refreshToken };
  const response = await apiClient.post(API_PATH.auth.refresh, body);
  return response.data;
};

export const logoutUser = async ({ refreshToken }) => {
  const body = { refresh_token: refreshToken };
  await apiClient.post(API_PATH.auth.logout, body);
};
