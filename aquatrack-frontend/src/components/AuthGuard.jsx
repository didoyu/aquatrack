import { Navigate } from "react-router-dom";
import { auth } from "../api.js";
import Layout from "./Layout.jsx";

export default function AuthGuard({ children, superuserOnly = false }) {
  if (!auth.loggedIn()) return <Navigate to="/login" replace />;
  if (superuserOnly && auth.user()?.is_superuser !== true) return <Navigate to="/" replace />;
  return <Layout>{children}</Layout>;
}