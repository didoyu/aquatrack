import { api } from "../api.js";
import useLoad from "../hooks/useLoad.js";
import { when } from "../utils/format.js";

export default function Admin() {
  const devices = useLoad(() => api("/devices/"));
  const logs = useLoad(() => api("/logs/?page_size=20"));

  return <><h1>Devices & system logs</h1><p className="sub">For maintenance staff. Register new devices in the Swagger docs or Django admin (the API key is shown once).</p>
    <div className="card"><h2>Devices</h2><table><thead><tr><th>Name</th><th>Status</th><th>Last seen</th><th>Firmware</th></tr></thead>
      <tbody>{devices.data?.results?.map((device) => <tr key={device.id}><td>{device.device_name}</td><td><span className={`badge ${device.status}`}>{device.status}</span></td><td>{when(device.last_seen)}</td><td>{device.firmware_version || "-"}</td></tr>)}</tbody></table></div>
    <div className="card" style={{ marginTop: 16 }}><h2>System logs</h2><table><tbody>{logs.data?.results?.map((log) => <tr key={log.id}><td>{when(log.created_at)}</td><td><span className={`badge ${log.level}`}>{log.level}</span></td><td>{log.message}</td></tr>)}</tbody></table></div>
  </>;
}