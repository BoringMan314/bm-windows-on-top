@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo [build_win10+win7] run build_win10 then build_win7
call "%~dp0build_win10.bat" nopause
if errorlevel 1 (
  echo [build_win10+win7] FAIL: build_win10.bat
  goto :end_fail
)
call "%~dp0build_win7.bat" nopause
if errorlevel 1 (
  echo [build_win10+win7] FAIL: build_win7.bat
  goto :end_fail
)
echo [build_win10+win7] OK: bm-windows-on-top.exe and bm-windows-on-top_win7.exe
goto :end_ok

:end_fail
if /i "%~1"=="nopause" exit /b 1
echo.
pause
exit /b 1

:end_ok
if /i "%~1"=="nopause" exit /b 0
echo.
pause
exit /b 0
