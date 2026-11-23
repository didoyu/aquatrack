import { useState } from "react";
import { api } from "../api.js";
import BarChart from "../components/BarChart.jsx";
import useHousehold from "../hooks/useHousehold.js";
import useLoad from "../hooks/useLoad.js";
import { fmt, when } from "../utils/format.js";

export default function Usage() {
  const household = useHousehold();
  const [period, setPeriod] = useState("daily");
  const usage = useLoad(() => (household ? api(`/households/${household.id}/usage/?period=${period}`) : Promise.resolve([])), [household?.id, period], 5000);
  const logs = useLoad(() => (household ? api(`/readings/?household=${household.id}&page_size=15`) : Promise.resolve(null)), [household?.id], 3000);
  const label = (reading) => {
    const date = new Date(reading.period_start);
    return period === "monthly" ? date.toLocaleString("en", { month: "short" }) : `${date.getMonth() + 1}/${date.getDate()}`;
  };

  return <><h1>Usage history</h1><p className="sub">Liters used per period.</p>
    <div className="tabs">{["daily", "weekly", "monthly"].map((value) => <button key={value} className={value === period ? "on" : ""} onClick={() => setPeriod(value)}>{value[0].toUpperCase() + value.slice(1)}</button>)}</div>
    <div className="card"><BarChart items={(usage.data || []).map((reading) => ({ label: label(reading), value: reading.total_consumption }))} /></div>
    <div className="card" style={{ marginTop: 16 }}><h2>Recent readings</h2><table><thead><tr><th>Time</th><th>Flow (L/min)</th><th>Pressure (PSI)</th><th>Status</th></tr></thead>
      <tbody>{logs.data?.results?.map((reading) => <tr key={reading.id}><td>{when(reading.timestamp)}</td><td>{fmt(reading.flow_rate, 2)}</td><td>{fmt(reading.pressure_level)}</td><td className={reading.is_anomalous ? "flag" : ""}>{reading.is_anomalous ? "Abnormal" : "Normal"}</td></tr>)}</tbody></table></div>
  </>;
}