/** Legacy PowerShell computer_open_app handler.
 *  Launches a Windows application by name via PowerShell. Deprecated
 *  in favor of the Python equivalent (FAZA 13). */

const { runPowerShell, psSingleQuote } = require("./runPowerShell.cjs");

async function computerOpenApp(appName) {
  await runPowerShell(`Start-Process ${psSingleQuote(appName)}`);
}

module.exports = { computerOpenApp };
