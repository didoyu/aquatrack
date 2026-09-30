import { fmt } from "../utils/format.js";

export default function BarChart({ items }) {
  const max = Math.max(...items.map((item) => item.value), 1);
  if (!items.length) return <p className="muted">No data yet. Start the simulator or connect a device.</p>;

  return <div className="bars">{items.map((item) => (
    <div className="bar" key={item.label}>
      <em>{fmt(item.value, item.value < 10 ? 1 : 0)}</em>
      <i style={{ height: `${(item.value / max) * 80}%` }} />
      <span>{item.label}</span>
    </div>
  ))}</div>;
}