import { api } from "../api.js";
import useHousehold from "../hooks/useHousehold.js";
import useLoad from "../hooks/useLoad.js";
import { fmt, when } from "../utils/format.js";

export default function Anomalies() {
  const household = useHousehold();
  const { data, reload, error } = useLoad(() => (household ? api(`/leaks/?household=${household.id}`) : Promise.resolve(null)), [household?.id]);
  const act = (id, action) => api(`/leaks/${id}/${action}/`, { method: "POST", body: {} }).then(reload);
  const names = ["Monitoring", "Stage 1 warning", "Stage 2 critical"];

  return <><h1>Leak detection</h1><p className="sub">Stage 1 alerts after 24 hours of abnormal flow. Stage 2 after 48 hours.</p>{error && <p className="err">{error}</p>}
    {data?.results?.length === 0 && <p className="muted">No anomalies recorded. Good news.</p>}
    {data?.results?.map((leak) => <div className="card" key={leak.id} style={{ marginBottom: 14 }}>
      <h2><span className={`badge s${leak.stage}`}>{names[leak.stage]}</span> {leak.classification} <span className="muted">· {leak.status}</span></h2>
      <p>Detected {when(leak.detected_at)} · lasted {fmt(leak.duration_hours, 1)} h · flow {fmt(leak.avg_flow_rate, 2)} L/min · pressure {fmt(leak.avg_pressure)} PSI</p>
      {leak.recommended_steps && <><b>{leak.recommended_steps.message}</b><ol className="check">{leak.recommended_steps.checklist.map((step) => <li key={step.priority}><b>{step.item}:</b> {step.how}</li>)}</ol></>}
      {!leak.resolved_at && <p><button onClick={() => act(leak.id, "inspect")}>Mark as inspected</button> <button className="ghost" onClick={() => act(leak.id, "false-alarm")}>False alarm</button> <button className="ghost" onClick={() => act(leak.id, "resolve")}>Mark fixed</button></p>}
    </div>)}
  </>;
}