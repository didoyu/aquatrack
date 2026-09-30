import { api } from "../api.js";
import BarChart from "../components/BarChart.jsx";
import useHousehold from "../hooks/useHousehold.js";
import useLoad from "../hooks/useLoad.js";
import { fmt, peso } from "../utils/format.js";

export default function Billing() {
  const household = useHousehold();
  const { data: forecast, error } = useLoad(() => (household ? api(`/billing/forecast/?household=${household.id}`) : Promise.resolve(null)), [household?.id]);
  if (error) return <p className="err">{error}</p>;
  if (!forecast) return <p className="muted">Calculating…</p>;

  return <><h1>Billing forecast</h1><p className="sub">Based on the COWD tiered residential rate ({forecast.schedule}).</p>
    <div className="grid"><div className="card hero stat"><small>Estimated bill this month</small><b>{peso(forecast.predicted_bill)}</b></div>
      <div className="card stat"><small>Used so far</small><b>{fmt(forecast.consumed_to_date, 2)} cu.m</b></div>
      <div className="card stat"><small>Projected for the month</small><b>{fmt(forecast.predicted_consumption, 2)} cu.m</b></div>
      <div className="card stat"><small>Cost per cubic meter</small><b>{peso(forecast.cost_per_cubic_meter)}</b></div></div>
    <div className="card"><h2>Monthly usage (cu.m)</h2><BarChart items={forecast.monthly_usage.map((month) => ({ label: month.month.slice(5, 7), value: month.cubic_meters }))} /></div>
    <div className="card" style={{ marginTop: 16 }}><h2>How the bill is computed</h2><table><tbody>{forecast.breakdown.map((item) => <tr key={item.label}><td>{item.label}</td><td>{fmt(item.cubic_meters, 2)} cu.m</td><td>{item.rate ? `${peso(item.rate)}/cu.m` : ""}</td><td>{peso(item.amount)}</td></tr>)}</tbody></table></div>
  </>;
}