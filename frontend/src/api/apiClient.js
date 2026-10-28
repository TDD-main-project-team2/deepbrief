import axios from "axios";
import { API_PATH } from "./config/paths.js";
import {
  getAccessToken,
  getRefreshToken,
  getAuthSessionVersion,
  saveTokens,
  removeTokens,
} from "../utils/tokenStorage.js";

const apiClient = axios.create({
  baseURL: "/api",
});

// API 요청에 보낼 인증 헤더를 만듭니다. 토큰을 넘기지 않으면 저장된 토큰을 사용합니다.
export const authConfig = (accessToken = getAccessToken()) =>
  accessToken ? { headers: { Authorization: `Bearer ${accessToken}` } } : {};

let refreshPromise = null; // 토큰을 재발급 중이면 다른 요청도 이 결과를 함께 기다립니다.
const authPaths = Object.values(API_PATH.auth);

// 토큰을 더 이상 사용할 수 없으면 저장된 토큰을 지우고 App에 로그아웃을 알립니다.
// 요청 도중 다른 계정으로 로그인했다면 새 로그인 상태는 건드리지 않습니다.
function expireSession(requestSessionVersion) {
  if (getAuthSessionVersion() !== requestSessionVersion) return;
  removeTokens();
  window.dispatchEvent(new Event("auth:expired"));
}

// 요청을 보낼 때 로그인 상태를 기억하고, 인증 헤더가 없으면 액세스 토큰을 붙입니다.
apiClient.interceptors.request.use((config) => {
  config._authSessionVersion = config._authSessionVersion ?? getAuthSessionVersion();
  const accessToken = getAccessToken();

  if (accessToken && !config.headers.has("Authorization")) {
    config.headers.set("Authorization", `Bearer ${accessToken}`);
  }

  return config;
});

// 리프레시 토큰으로 새 액세스·리프레시 토큰을 받아 저장합니다.
// 기다리는 동안 로그아웃하거나 다시 로그인했다면 받은 토큰을 저장하지 않습니다.
async function renewTokens(requestSessionVersion) {
  const { data } = await axios.post(`/api${API_PATH.auth.refresh}`, {
    refresh_token: getRefreshToken(),
  });

  if (getAuthSessionVersion() !== requestSessionVersion) {
    throw new axios.CanceledError("Session changed");
  }

  if (!data.access_token || !data.refresh_token) throw new Error("Invalid token response");

  saveTokens(
    { accessToken: data.access_token, refreshToken: data.refresh_token },
    { refresh: true },
  );
}

// 일반 API가 401을 반환하면 토큰을 재발급하고 원래 요청을 한 번 다시 보냅니다.
// 재발급에 실패하거나 재시도도 401이면 로그아웃 처리합니다.
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config;
    if (error.response?.status !== 401 || !config || authPaths.includes(config.url)) throw error;

    const requestSessionVersion = config._authSessionVersion;
    if (getAuthSessionVersion() !== requestSessionVersion) throw error;

    try {
      // 이미 재시도했거나 리프레시 토큰이 없으면 로그아웃 처리로 넘어갑니다.
      if (config._retried || !getRefreshToken()) throw error;
      config._retried = true;

      // 실패한 요청의 토큰이 아직 저장된 토큰과 같을 때만 재발급이 필요합니다.
      // 저장된 토큰이 이미 바뀌었다면 아래에서 새 토큰으로 바로 다시 요청합니다.
      if (config.headers.get("Authorization") === `Bearer ${getAccessToken()}`) {
        refreshPromise =
          refreshPromise ??
          renewTokens(requestSessionVersion).finally(() => {
            refreshPromise = null;
          });
        await refreshPromise;
      }

      if (getAuthSessionVersion() !== requestSessionVersion) {
        throw new axios.CanceledError("Session changed");
      }
    } catch (refreshError) {
      expireSession(requestSessionVersion);
      throw refreshError;
    }

    config.headers.set("Authorization", `Bearer ${getAccessToken()}`);

    return apiClient(config);
  },
);

export default apiClient;
