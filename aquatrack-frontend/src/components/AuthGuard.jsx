import { Navigate } from "react-router-dom";
import { auth } from "../api.js";
import Layout from "./Layout.jsx";

export default function AuthGuard({ children }) {
  return auth.loggedIn() ? <Layout>{children}</Layout> : <Navigate to="/login" replace />;
}