import { Navigate, Route, Routes } from "react-router-dom";
import AuthGuard from "./components/AuthGuard.jsx";
import AuthPage from "./pages/AuthPage.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Usage from "./pages/Usage.jsx";
import Anomalies from "./pages/Anomalies.jsx";
import Billing from "./pages/Billing.jsx";
import Alerts from "./pages/Alerts.jsx";
import Admin from "./pages/Admin.jsx";

export default function App() {
  return <Routes>
    <Route path="/login" element={<AuthPage />} />
    <Route path="/register" element={<AuthPage register />} />
    <Route path="/" element={<AuthGuard><Dashboard /></AuthGuard>} />
    <Route path="/usage" element={<AuthGuard><Usage /></AuthGuard>} />
    <Route path="/anomalies" element={<AuthGuard><Anomalies /></AuthGuard>} />
    <Route path="/billing" element={<AuthGuard><Billing /></AuthGuard>} />
    <Route path="/alerts" element={<AuthGuard><Alerts /></AuthGuard>} />
    <Route path="/admin" element={<AuthGuard superuserOnly><Admin /></AuthGuard>} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>;
}