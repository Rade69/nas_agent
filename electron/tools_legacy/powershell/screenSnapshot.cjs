const fs = require("node:fs/promises");
const path = require("node:path");
const { runPowerShell, psSingleQuote } = require("./runPowerShell.cjs");

async function screenSnapshot(dataDir) {
  await fs.mkdir(dataDir, { recursive: true });
  const screenshotPath = path.join(dataDir, `screenshot-${Date.now()}.png`);
  const script = `Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$bounds = [System.Windows.Forms.SystemInformation]::VirtualScreen
$bitmap = New-Object System.Drawing.Bitmap($bounds.Width, $bounds.Height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
$bitmap.Save(${psSingleQuote(screenshotPath)}, [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bitmap.Dispose()`;
  await runPowerShell(script);
  return screenshotPath;
}

module.exports = { screenSnapshot };
