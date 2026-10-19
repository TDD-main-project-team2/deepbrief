import axios from "axios";
import { getAccessToken } from "../utils/tokenStorage.js";

const apiClient = axios.create({
  baseURL: "/api",
});

export const authConfig = (accessToken = getAccessToken()) =>
  accessToken ? { headers: { Authorization: `Bearer ${accessToken}` } } : {};

apiClient.interceptors.request.use((config) => {
  const accessToken = getAccessToken();

  if (accessToken && !config.headers.has("Authorization")) {
    config.headers.set("Authorization", `Bearer ${accessToken}`);
  }

  return config;
});

export default apiClient;
