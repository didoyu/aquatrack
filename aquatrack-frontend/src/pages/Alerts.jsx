import { api } from "../api.js";
import useHousehold from "../hooks/useHousehold.js";
import useLoad from "../hooks/useLoad.js";
import { when } from "../utils/format.js";

export default function Alerts() {
  const household = useHousehold();
  const { data, reload } = useLoad(() => (household ? api(`/alerts/?household=${household.id}`) : Promise.resolve(null)), [household?.id], 15000);

  return <><h1>Alerts</h1><p className="sub">Leak warnings and device notices.</p>
    {data?.results?.length === 0 && <p className="muted">No alerts yet.</p>}
    {data?.results?.map((alert) => <div className="card" key={alert.id} style={{ marginBottom: 10, opacity: alert.is_read ? 0.65 : 1 }}>
      <span className={`badge ${alert.severity}`}>{alert.severity}</span> <b>{alert.alert_type.replace("_", " ")}</b> <span className="muted">{when(alert.sent_at)}</span>
      <p>{alert.message}</p>{!alert.is_read && <button className="ghost" onClick={() => api(`/alerts/${alert.id}/read/`, { method: "POST" }).then(reload)}>Mark as read</button>}
    </div>)}
  </>;
}