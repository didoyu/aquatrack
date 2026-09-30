import { NavLink, useNavigate } from "react-router-dom";
import { api, auth } from "../api.js";
import useLoad from "../hooks/useLoad.js";

export default function Layout({ children }) {
  const navigate = useNavigate();
  const user = auth.user();
  const unread = useLoad(() => api("/alerts/unread-count/"), [], 15000).data?.unread;
  const links = [["/", "Dashboard"], ["/usage", "Usage history"], ["/anomalies", "Leak detection"], ["/billing", "Billing forecast"], ["/alerts", `Alerts${unread ? ` (${unread})` : ""}`]];
  if (user?.role !== "homeowner") links.push(["/admin", "Devices & logs"]);

  return <div className="shell"><nav className="side" aria-label="Main">
    <div className="brand">Aqua<span>Track</span></div>
    {links.map(([to, label]) => <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => (isActive ? "active" : "")}>{label}</NavLink>)}
    <div className="who">{user?.first_name} {user?.last_name}<br />{user?.email}
      <button className="ghost" onClick={() => { auth.clear(); navigate("/login"); }}>Log out</button>
    </div>
  </nav><main>{children}</main></div>;
}