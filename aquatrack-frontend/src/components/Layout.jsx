import { NavLink, useNavigate } from "react-router-dom";
import { api, auth } from "../api.js";
import useLoad from "../hooks/useLoad.js";

export default function Layout({ children }) {
  const navigate = useNavigate();
  const user = auth.user();
  const unread = useLoad(() => api("/alerts/unread-count/"), [], 15000).data?.unread;
  const links = [["/", "Dashboard"], ["/usage", "Usage history"], ["/anomalies", "Leak detection"], ["/billing", "Billing forecast"], ["/alerts", `Alerts${unread ? ` (${unread})` : ""}`]];
  if (user?.is_superuser === true) links.push(["/admin", "Devices & logs"]);

  return <div className="shell"><aside className="side">
    <div className="brand"><img className="brand-logo" src="/aquatrack-logo.png" alt="" aria-hidden="true" /><span className="brand-name"><span className="brand-aqua">Aqua</span><span className="brand-track">Track</span></span></div>
    <div className="nav-label">Water overview</div>
    <nav className="nav-links" aria-label="Main navigation">
      {links.map(([to, label]) => <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => (isActive ? "active" : "")}>{label}</NavLink>)}
    </nav>
    <div className="who"><strong>{user?.first_name} {user?.last_name}</strong><span className="email">{user?.email}</span>
      <button className="ghost" onClick={() => { auth.clear(); navigate("/login"); }}>Log out</button>
    </div>
  </aside><main><div className="page-content">{children}</div></main></div>;
}