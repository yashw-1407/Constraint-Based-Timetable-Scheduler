@echo off
setlocal
cd /d "%~dp0"
echo Creating desktop shortcut for Academic Timetable Scheduler...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$desktop = [Environment]::GetFolderPath('Desktop');" ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "$s = $ws.CreateShortcut((Join-Path $desktop 'Academic Timetable Scheduler.lnk'));" ^
  "$s.TargetPath = '%~dp0run.bat';" ^
  "$s.WorkingDirectory = '%~dp0';" ^
  "$s.Description = 'Launch Academic Timetable Scheduler';" ^
  "$s.IconLocation = 'shell32.dll,14';" ^
  "$s.Save();" ^
  "Write-Host 'Desktop shortcut successfully created!'"
echo.
pause
