import apiClient from "./apiClient.js";
import { API_PATH } from "./config/paths.js";

export const signupUser = async ({ email, password, nickname, organizationCode, adminCode }) => {
  const body = {
    email,
    password,
    nickname,
    organization_code: organizationCode,
    admin_code: adminCode || null,
  };
  const response = await apiClient.post(API_PATH.auth.register, body);
  return response.data;
};

export const loginUser = async ({ email, password }) => {
  const body = { email, password };
  const response = await apiClient.post(API_PATH.auth.login, body);
  return response.data;
};

export const logoutUser = async ({ refreshToken }) => {
  const body = { refresh_token: refreshToken };
  await apiClient.post(API_PATH.auth.logout, body);
};
