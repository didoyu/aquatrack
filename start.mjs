import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.dirname(fileURLToPath(import.meta.url));
const backendDir = path.join(root, "aquatrack-backend");
const frontendDir = path.join(root, "aquatrack-frontend");

const venvPython = process.platform === "win32"
  ? path.join(backendDir, ".venv", "Scripts", "python.exe")
  : path.join(backendDir, ".venv", "bin", "python");
const python = existsSync(venvPython) ? venvPython : "python";
const npmCmd = process.platform === "win32" ? "npm.cmd" : "npm";

function pipePrefixed(stream, label, out) {
  let buf = "";
  stream.on("data", (chunk) => {
    buf += chunk.toString();
    const lines = buf.split(/\r?\n/);
    buf = lines.pop() ?? "";
    for (const line of lines) out.write(`[${label}] ${line}\n`);
  });
  stream.on("end", () => { if (buf) out.write(`[${label}] ${buf}\n`); });
}

const children = [];
function launch(label, cmd, args, cwd) {
  const proc = spawn(cmd, args, {
    cwd,
    stdio: ["ignore", "pipe", "pipe"],
    shell: process.platform === "win32" && cmd.endsWith(".cmd"),
  });
  pipePrefixed(proc.stdout, label, process.stdout);
  pipePrefixed(proc.stderr, label, process.stderr);
  children.push(proc);
  return proc;
}

// ponytail: built-in Windows .NET SerialPort fallback so USB-connected ESP32 streams live readings even when Wi-Fi hotspot fails
const usbBridgeScript = `
$key = 'ydwqBbiuvYBzxTwyiEEnI5Ju6sGGayGGBxSsNfJssrc'
$base = 'http://127.0.0.1:8000/api/ingest'
$headers = @{ 'X-Device-Key' = $key; 'Content-Type' = 'application/json' }
$warnedBusy = $false
Start-Sleep -Seconds 3

while ($true) {
  $ports = [System.IO.Ports.SerialPort]::GetPortNames()
  $portName = if ($ports -contains 'COM3') { 'COM3' } elseif ($ports.Count -gt 0) { $ports[0] } else { $null }
  if (-not $portName) { Start-Sleep -Seconds 3; continue }

  $sp = New-Object System.IO.Ports.SerialPort $portName, 115200, 'None', 8, 'one'
  $sp.ReadTimeout = 1500
  $sp.DtrEnable = $false
  $sp.RtsEnable = $false
  try {
    $sp.Open()
    $warnedBusy = $false
    Write-Output "Connected to ESP32 on $portName (USB Serial bridge active)"
    try {
      Invoke-RestMethod -Uri "$base/heartbeat/" -Method Post -Headers $headers -Body '{"firmware_version":"1.0.0-usb"}' -TimeoutSec 3 | Out-Null
      Write-Output "Heartbeat sent -> ESP32-01 is now ONLINE"
    } catch {}

    $sumFlow = 0.0; $count = 0; $lastVol = 0.0; $wifiOk = $false
    while ($sp.IsOpen) {
      try {
        $line = $sp.ReadLine().Trim()
      } catch [System.TimeoutException] { continue }
      if (-not $line) { continue }
      Write-Output $line
      if ($line -match 'HTTP 201') { $wifiOk = $true }
      if ($line -match 'Flow rate:\\s*([0-9.]+)\\s*L/min\\s*\\|\\s*Total:\\s*([0-9.]+)\\s*L') {
        $sumFlow += [double]$Matches[1]
        $lastVol = [double]$Matches[2]
        $count++
        if (-not $wifiOk -and $count -ge 3) {
          $avg = [math]::Round($sumFlow / $count, 3)
          $body = (@{ flow_rate = $avg; water_volume = $lastVol; sampling_interval = $count; edge_flag = $false } | ConvertTo-Json -Compress)
          try {
            Invoke-RestMethod -Uri "$base/readings/" -Method Post -Headers $headers -Body $body -TimeoutSec 3 | Out-Null
            Write-Output "Forwarded to AquaTrack -> flow=$avg L/min, total=$lastVol L"
          } catch {}
          $sumFlow = 0.0; $count = 0
        }
      }
    }
  } catch {
    if ($_.Exception.Message -match 'Access to the port' -and -not $warnedBusy) {
      Write-Output "$portName is currently open in Arduino IDE Serial Monitor. Close Serial Monitor in Arduino IDE to let AquaTrack stream live readings over USB."
      $warnedBusy = $true
    }
    if ($sp.IsOpen) { try { $sp.Close() } catch {} }
    Start-Sleep -Seconds 2
  }
}
`;

let stopping = false;
function shutdown(code = 0) {
  if (stopping) return;
  stopping = true;
  for (const child of children) {
    if (!child.pid || child.killed) continue;
    if (process.platform === "win32") {
      // ponytail: taskkill /T terminates the npm.cmd + vite process tree on Windows
      spawn("taskkill", ["/pid", String(child.pid), "/t", "/f"], { stdio: "ignore" });
    } else {
      child.kill("SIGTERM");
    }
  }
  setTimeout(() => process.exit(code), 300);
}

process.on("SIGINT", () => shutdown(0));
process.on("SIGTERM", () => shutdown(0));

const lanIps = Object.values(os.networkInterfaces()).flat()
  .filter((n) => n && n.family === "IPv4" && !n.internal && !n.address.startsWith("169.254."))
  .map((n) => n.address);
console.log("Starting AquaTrack backend (0.0.0.0:8000) and frontend (http://localhost:5173)...");
if (lanIps.length) console.log(`ESP32 SERVER_URL candidates: ${lanIps.map((ip) => `http://${ip}:8000`).join(", ")}`);
const backend = launch("backend", python, ["manage.py", "runserver", "0.0.0.0:8000"], backendDir);
const frontend = launch("frontend", npmCmd, ["run", "dev"], frontendDir);
if (process.platform === "win32") {
  launch("esp32-usb", "powershell.exe", ["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", usbBridgeScript], root);
}

backend.on("exit", (code) => {
  if (!stopping) {
    console.error(`[backend] exited with code ${code ?? 1}`);
    shutdown(code ?? 1);
  }
});
frontend.on("exit", (code) => {
  if (!stopping) {
    console.error(`[frontend] exited with code ${code ?? 1}`);
    shutdown(code ?? 1);
  }
});
