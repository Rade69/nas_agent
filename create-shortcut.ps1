$scriptDir = $PSScriptRoot
$batPath = Join-Path $scriptDir "Pokreni-Ricky.bat"
$shortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "Ricky.lnk"
$electronIcon = Join-Path $scriptDir "node_modules\electron\dist\electron.exe"

$WshShell = New-Object -ComObject WScript.Shell
$shortcut = $WshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $batPath
$shortcut.WorkingDirectory = $scriptDir
if (Test-Path $electronIcon) {
  $shortcut.IconLocation = "$electronIcon,0"
} else {
  $shortcut.IconLocation = "$env:SystemRoot\System32\SHELL32.dll,220"
}
$shortcut.WindowStyle = 1
$shortcut.Description = "Pokreni Ricky - AI glasovni asistent"
$shortcut.Save()

Write-Host "Precica napravljena na Desktopu: $shortcutPath"
