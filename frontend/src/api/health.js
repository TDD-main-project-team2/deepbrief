import apiClient from "./apiClient.js";
import { API_PATH } from "./config/paths.js";

export const getHealth = async () => {
  const response = await apiClient.get(API_PATH.health);
  return response.data;
};
