/** Legacy PowerShell computer_scroll handler.
 *  Simulates mouse scroll wheel input via PowerShell. Deprecated in
 *  favor of the Python equivalent (FAZA 13). */

const { runPowerShell, NATIVE_MOUSE_TYPE } = require("./runPowerShell.cjs");

async function computerScroll(direction, amount) {
  const resolvedDirection = String(direction || "down");
  const boundedAmount = Math.max(1, Math.min(20, Number(amount || 4)));
  const wheelDelta = 120 * boundedAmount;
  const isHorizontal = resolvedDirection === "left" || resolvedDirection === "right";
  const flags = isHorizontal ? "0x1000" : "0x0800";
  const dwData = resolvedDirection === "down" || resolvedDirection === "left" ? -wheelDelta : wheelDelta;
  const script = `${NATIVE_MOUSE_TYPE}
[RickyNativeMouse]::mouse_event(${flags}, 0, 0, ${dwData}, [UIntPtr]::Zero)`;
  await runPowerShell(script);
  return resolvedDirection;
}

module.exports = { computerScroll };
