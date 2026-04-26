@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "OUT=bm-windows-on-top_win7.exe"
set "PIPY="

echo [build_win7] Build Win7+tkinter: %OUT%
echo [build_win7] cleaning build/dist contents, exe in project root
taskkill /F /IM "%OUT%" /T >nul 2>&1
if not exist "build" mkdir "build" 2>nul
if not exist "dist" mkdir "dist" 2>nul
call :clean_dir_contents "build"
call :clean_dir_contents "dist"
if exist "bm-windows-on-top.spec" del /f /q "bm-windows-on-top.spec" 2>nul
if exist "bm-windows-on-top_win7.spec" del /f /q "bm-windows-on-top_win7.spec" 2>nul
if exist "%OUT%" del /f /q "%OUT%" 2>nul

call :find_python
if errorlevel 1 goto :end_fail

echo [build_win7] using:
%PIPY% -c "import sys; print(sys.executable); print(sys.version)"

%PIPY% -c "import sys; assert sys.version_info[:2]==(3,8), 'need_38_only'" 2>nul
if errorlevel 1 (
  echo [build_win7] FAIL: require Python 3.8.x only
  goto :end_fail
)

%PIPY% -m pip install -q -r requirements-win7.txt
if errorlevel 1 (
  echo [build_win7] FAIL: pip install
  goto :end_fail
)

%PIPY% build.py win7
if errorlevel 1 (
  echo [build_win7] FAIL: build.py
  goto :end_fail
)

if not exist "%OUT%" (
  echo [build_win7] FAIL: missing %OUT%
  goto :end_fail
)

echo [build_win7] OK: %CD%\%OUT%
goto :end_ok

:find_python
set "PIPY="
where py >nul 2>&1
if not errorlevel 1 (
  py -3.8 -c "import sys; assert sys.version_info[:2]==(3,8)" 2>nul
  if not errorlevel 1 (
    set "PIPY=py -3.8"
    goto :find_ok
  )
)
where python >nul 2>&1
if not errorlevel 1 (
  python -c "import sys; assert sys.version_info[:2]==(3,8)" 2>nul
  if not errorlevel 1 (
    set "PIPY=python"
    goto :find_ok
  )
)
echo [build_win7] FAIL: Python 3.8.x required (use: py -3.8 or python 3.8 on PATH)
exit /b 1
:find_ok
exit /b 0

:clean_dir_contents
set "TGT=%~1"
if not exist "%TGT%" exit /b 0
for /f "delims=" %%D in ('dir /b /ad "%TGT%" 2^>nul') do rd /s /q "%TGT%\%%D" 2>nul
del /f /q "%TGT%\*" 2>nul
exit /b 0

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
