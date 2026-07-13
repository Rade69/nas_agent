/** Legacy PowerShell computer_press_key handler.
 *  Sends a keystroke to the active window via PowerShell. Deprecated
 *  in favor of the Python equivalent (FAZA 13). */

const { runPowerShell, psSingleQuote } = require("./runPowerShell.cjs");

const KEY_TOKENS = {
  enter: "{ENTER}",
  return: "{ENTER}",
  tab: "{TAB}",
  escape: "{ESC}",
  delete: "{DEL}",
  space: " ",
  up: "{UP}",
  down: "{DOWN}",
  left: "{LEFT}",
  right: "{RIGHT}",
};

function sendKeysForKey(key) {
  return KEY_TOKENS[String(key || "").toLowerCase()] || null;
}

// Context: agent_reports/2026-07-05_split-main-cjs-faza3.md
// Throws instead of returning {ok:false} directly (original inline behavior) so main.cjs's
// existing outer try/catch in the tools:execute dispatcher formats the error identically.
async function computerPressKey(key, repeat) {
  const keyToken = sendKeysForKey(key);
  if (!keyToken) {
    throw new Error(`Unsupported key: ${key}`);
  }
  const boundedRepeat = Math.max(1, Math.min(20, Number(repeat || 1)));
  const repeated = keyToken.repeat(boundedRepeat);
  const script = `Add-Type -AssemblyName System.Windows.Forms\n[System.Windows.Forms.SendKeys]::SendWait(${psSingleQuote(repeated)})`;
  await runPowerShell(script);
}

module.exports = { computerPressKey };
