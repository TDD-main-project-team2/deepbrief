// 로그인하거나 로그아웃할 때 바뀌는 번호입니다. 토큰만 자동 갱신할 때는 유지합니다.
let authSessionVersion = 0;

// 요청 전후에 이 번호를 비교하면 같은 로그인 상태인지 확인할 수 있습니다.
export const getAuthSessionVersion = () => authSessionVersion;

// 두 토큰을 브라우저에 저장합니다. 자동 갱신 시 refresh: true를 넘겨 로그인 번호를 유지합니다.
export function saveTokens({ accessToken, refreshToken }, { refresh = false } = {}) {
  if (!refresh) authSessionVersion += 1;
  localStorage.setItem("accessToken", accessToken);
  localStorage.setItem("refreshToken", refreshToken);
}

export function getAccessToken() {
  return localStorage.getItem("accessToken");
}

export function getRefreshToken() {
  return localStorage.getItem("refreshToken");
}

// 두 토큰을 지우고 로그인 번호를 바꿔, 이전 로그인에서 보낸 응답을 구분할 수 있게 합니다.
export function removeTokens() {
  authSessionVersion += 1;
  localStorage.removeItem("accessToken");
  localStorage.removeItem("refreshToken");
}
