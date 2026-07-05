const { execFile } = require("node:child_process");
const { promisify } = require("node:util");

const execFileAsync = promisify(execFile);

async function runPowerShell(script) {
  return execFileAsync("powershell.exe", ["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script]);
}

function psSingleQuote(value) {
  return `'${String(value).replace(/'/g, "''")}'`;
}

const NATIVE_MOUSE_TYPE = `
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class RickyNativeMouse {
  [DllImport("user32.dll")]
  public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")]
  public static extern void mouse_event(uint dwFlags, int dx, int dy, int dwData, UIntPtr dwExtraInfo);
}
"@
`;

const NATIVE_WINDOW_TYPE = `
Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public class RickyNativeWindow {
  [DllImport("user32.dll")]
  public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")]
  public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
  [DllImport("user32.dll")]
  public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
}
"@
`;

module.exports = { runPowerShell, psSingleQuote, NATIVE_MOUSE_TYPE, NATIVE_WINDOW_TYPE };
