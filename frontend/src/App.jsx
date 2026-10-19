import { useState } from "react";
import { Routes, Route } from "react-router";

import MainPage from "./pages/MainPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import SignupPage from "./pages/SignupPage.jsx";
import apiClient from "./api/apiClient.js";

export default function App() {
  const [session, setSession] = useState(null);

  function handleLogin(session) {
    apiClient.defaults.headers.common.Authorization = `Bearer ${session.access_token}`;
    setSession(session);
  }

  function handleLogout() {
    delete apiClient.defaults.headers.common.Authorization;
    setSession(null);
  }

  return (
    <Routes>
      <Route
        path="/"
        element={<MainPage user={session?.user} onLogout={handleLogout} />}
      />
      <Route path="/login" element={<LoginPage onLogin={handleLogin} />} />
      <Route path="/signup" element={<SignupPage />} />
    </Routes>
  );
}
