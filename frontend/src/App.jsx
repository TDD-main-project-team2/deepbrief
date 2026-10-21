import { useEffect, useState } from "react";
import { Routes, Route } from "react-router";

import MainPage from "./pages/MainPage.jsx";
import AdminPage from "./pages/AdminPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import SignupPage from "./pages/SignupPage.jsx";

import CompletionNotice from "./components/common/feedback/CompletionNotice.jsx";
import ProtectedRoute from "./ProtectedRoute.jsx";

import { getCurrentUser } from "./api/users.js";
import { logoutUser } from "./api/auth.js";
import {
  getAccessToken,
  getAuthSessionVersion,
  getRefreshToken,
  saveTokens,
  removeTokens,
} from "./utils/tokenStorage.js";

export default function App() {
  const [session, setSession] = useState(null);
  const [completionMessage, setCompletionMessage] = useState("");
  const [restoringSession, setRestoringSession] = useState(() => Boolean(getAccessToken())); // 새로고침 후 저장된 토큰으로 로그인 상태를 확인 중인지 나타내는 값

  useEffect(() => {
    const accessToken = getAccessToken();
    const requestSessionVersion = getAuthSessionVersion();
    if (!accessToken) return;

    let cancelled = false;

    async function loadUser() {
      try {
        const user = await getCurrentUser(accessToken);
        if (!cancelled && getAuthSessionVersion() === requestSessionVersion) {
          setSession({ user });
        }
      } catch (error) {
        if (
          !cancelled &&
          getAuthSessionVersion() === requestSessionVersion &&
          error.response?.status === 401
        ) {
          removeTokens();
        }
      } finally {
        if (!cancelled) setRestoringSession(false);
      }
    }

    loadUser();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    function handleExpiredSession() {
      setSession(null);
      setRestoringSession(false);
    }
    window.addEventListener("auth:expired", handleExpiredSession);
    return () => window.removeEventListener("auth:expired", handleExpiredSession);
  }, []);

  function handleLogin(session) {
    saveTokens({
      accessToken: session.access_token,
      refreshToken: session.refresh_token,
    });

    setSession(session);
    setRestoringSession(false);
  }

  async function handleLogout() {
    const refreshToken = getRefreshToken();

    removeTokens();
    setSession(null);
    setRestoringSession(false);
    setCompletionMessage("로그아웃 되었습니다.");

    if (refreshToken) {
      try {
        await logoutUser({ refreshToken });
      } catch {
        // 서버 요청이 실패해도 브라우저의 로그아웃 상태는 유지합니다.
      }
    }
  }

  return (
    <>
      <CompletionNotice message={completionMessage} onClose={() => setCompletionMessage("")} />
      <Routes>
        <Route
          path="/"
          element={
            <ProtectedRoute user={session?.user} loading={restoringSession}>
              <MainPage
                key={session?.user?.id}
                user={session?.user}
                onLogout={handleLogout}
                onComplete={setCompletionMessage}
              />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin"
          element={
            <ProtectedRoute user={session?.user} loading={restoringSession} requiredRole="admin">
              <AdminPage key={session?.user?.id} user={session?.user} onLogout={handleLogout} />
            </ProtectedRoute>
          }
        />
        <Route path="/login" element={<LoginPage onLogin={handleLogin} />} />
        <Route path="/signup" element={<SignupPage />} />
      </Routes>
    </>
  );
}
