import { Navigate } from "react-router";

export default function ProtectedRoute({ user, loading, children }) {
  if (loading) {
    return <main role="status">로그인 확인 중...</main>;
  }

  if (!user) return <Navigate to="/login" replace />;

  return children;
}
