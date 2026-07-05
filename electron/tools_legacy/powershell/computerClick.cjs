const { runPowerShell, NATIVE_MOUSE_TYPE } = require("./runPowerShell.cjs");

async function computerClick(x, y) {
  const script = `${NATIVE_MOUSE_TYPE}
[RickyNativeMouse]::SetCursorPos(${Number(x) | 0}, ${Number(y) | 0})
Start-Sleep -Milliseconds 50
[RickyNativeMouse]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
[RickyNativeMouse]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)`;
  await runPowerShell(script);
}

module.exports = { computerClick };
