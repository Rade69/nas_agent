const { runPowerShell, psSingleQuote } = require("./runPowerShell.cjs");

async function computerOpenApp(appName) {
  await runPowerShell(`Start-Process ${psSingleQuote(appName)}`);
}

module.exports = { computerOpenApp };
