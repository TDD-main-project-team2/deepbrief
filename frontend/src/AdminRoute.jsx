import { Navigate } from "react-router";

function AdminRoute({ user, loading, children }) {
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "admin") return <Navigate to="/" replace />;
  return children;
}

export default AdminRoute;