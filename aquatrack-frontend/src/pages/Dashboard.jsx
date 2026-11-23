import { NavLink } from "react-router-dom";
import { api } from "../api.js";
import useHousehold from "../hooks/useHousehold.js";
import useLoad from "../hooks/useLoad.js";
import { fmt, peso, when } from "../utils/format.js";

export default function Dashboard() {
  const household = useHousehold();
  const { data, error } = useLoad(() => (household ? api(`/households/${household.id}/dashboard/`) : Promise.resolve(null)), [household?.id], 3000);
  if (error) return <p className="err">{error}</p>;
  if (!data) return <p className="muted">Loading your household…</p>;
  const leak = data.active_leak;

  return <><header className="page-heading"><div><p className="eyebrow">Household water profile</p><h1>{data.household.name}</h1><p className="sub">Sensor readings and consumption at a glance. Last reading: {when(data.last_reading_at)}</p></div><span className="live-chip"><i /> Sensor overview</span></header>
    {leak && leak.stage > 0
      ? <div className={`banner s${leak.stage}`}><span>{leak.stage === 2 ? "Critical: abnormal flow for" : "Possible leak: abnormal flow for"} {fmt(leak.duration_hours, 0)} hours.</span><NavLink to="/anomalies">See what to do</NavLink></div>
      : <div className="banner s0"><span>{leak ? "Unusual flow detected. We are monitoring it." : "No leaks detected. Your water use looks normal."}</span></div>}
    <div className="grid">
      <div className="card hero stat"><small>Flow rate now</small><b>{fmt(data.current_flow_rate, 2)} L/min</b></div>
      <div className="card stat"><small>Pipe pressure</small><b>{fmt(data.current_pressure)} PSI</b></div>
      <div className="card stat"><small>Used today</small><b>{fmt(data.today_consumption_liters, 0)} L</b></div>
      <div className="card stat"><small>Highest day this month</small><b>{fmt(data.max_daily_consumption_liters, 0)} L</b></div>
      <div className="card stat"><small>Average per hour today</small><b>{fmt(data.average_hourly_usage_liters, 1)} L</b></div>
      <div className="card stat"><small>Projected bill this month</small><b>{peso(data.projected_bill)}</b></div>
    </div>
    <div className="card"><h2>Sensor units</h2>{data.devices.length ? <div className="device-list">{data.devices.map((device) => <div className="device-row" key={device.id}><div className="device-meta"><strong>{device.name}</strong><small>Last seen {when(device.last_seen)}</small></div><span className={`badge ${device.status}`}>{device.status}</span></div>)}</div> : <p className="muted">No device registered yet. Ask your AquaTrack administrator to add your ESP32.</p>}</div>
  </>;
}