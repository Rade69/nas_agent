/** Legacy PowerShell computer_type_text handler.
 *  Types text into the active window via PowerShell. Deprecated in
 *  favor of the Python equivalent (FAZA 13). */

const { runPowerShell, psSingleQuote } = require("./runPowerShell.cjs");

function escapeSendKeys(text) {
  return String(text)
    .replace(/([+^%~(){}[\]])/g, "{$1}")
    .replace(/\r?\n/g, "{ENTER}");
}

async function computerTypeText(text) {
  const escaped = escapeSendKeys(String(text || ""));
  const script = `Add-Type -AssemblyName System.Windows.Forms\n[System.Windows.Forms.SendKeys]::SendWait(${psSingleQuote(escaped)})`;
  await runPowerShell(script);
}

module.exports = { computerTypeText };
