const { runPowerShell, NATIVE_WINDOW_TYPE } = require("./runPowerShell.cjs");

async function uiInspect() {
  const script = `${NATIVE_WINDOW_TYPE}
$hwnd = [RickyNativeWindow]::GetForegroundWindow()
$sb = New-Object System.Text.StringBuilder 256
[RickyNativeWindow]::GetWindowText($hwnd, $sb, 256) | Out-Null
$procId = 0
[RickyNativeWindow]::GetWindowThreadProcessId($hwnd, [ref]$procId) | Out-Null
$proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
$procName = if ($proc) { $proc.ProcessName } else { "Unknown" }
Write-Output ("App: " + $procName)
Write-Output ("Window: " + $sb.ToString())`;
  const { stdout } = await runPowerShell(script);
  return stdout.trim();
}

module.exports = { uiInspect };
