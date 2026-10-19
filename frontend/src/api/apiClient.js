import axios from "axios";

const apiClient = axios.create({
  baseURL: "/api",
});

export const authConfig = (accessToken) => ({
  headers: {
    Authorization: `Bearer ${accessToken}`,
  },
});

export default apiClient;
