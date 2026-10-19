import apiClient, { authConfig } from "./apiClient.js";
import { API_PATH } from "./config/paths.js";

export const getCurrentUser = async (accessToken) => {
  const response = await apiClient.get(API_PATH.users.me, authConfig(accessToken));
  return response.data;
};
