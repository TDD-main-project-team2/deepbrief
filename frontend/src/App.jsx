import { useEffect, useState } from "react";
import { Routes, Route } from "react-router";

import MainPage from "./pages/MainPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import SignupPage from "./pages/SignupPage.jsx";

import { getCurrentUser } from "./api/users.js";
import { logoutUser } from "./api/auth.js";
import { getAccessToken, getRefreshToken, saveTokens, removeTokens } from "./utils/tokenStorage.js";

export default function App() {
  const [session, setSession] = useState(null);

  useEffect(() => {
    const accessToken = getAccessToken();
    if (!accessToken) return;

    let cancelled = false;

    async function loadUser() {
      try {
        const user = await getCurrentUser(accessToken);
        if (!cancelled && getAccessToken() === accessToken) {
          setSession({ user });
        }
      } catch (error) {
        if (!cancelled && getAccessToken() === accessToken && error.response?.status === 401) {
          removeTokens();
        }
      }
    }

    loadUser();

    return () => {
      cancelled = true;
    };
  }, []);

  function handleLogin(session) {
    saveTokens({
      accessToken: session.access_token,
      refreshToken: session.refresh_token,
    });

    setSession(session);
  }

  async function handleLogout() {
    const refreshToken = getRefreshToken();
    removeTokens();
    setSession(null);

    if (refreshToken) {
      try {
        await logoutUser({ refreshToken });
      } catch {
        // 서버 요청이 실패해도 브라우저의 로그아웃 상태는 유지합니다.
      }
    }
  }

  return (
    <Routes>
      <Route path="/" element={<MainPage user={session?.user} onLogout={handleLogout} />} />
      <Route path="/login" element={<LoginPage onLogin={handleLogin} />} />
      <Route path="/signup" element={<SignupPage />} />
    </Routes>
  );
}
