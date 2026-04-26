@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "OUT=bm-windows-on-top.exe"
set "PIPY="

echo [build_win10] Build Win10+tkinter: %OUT%
echo [build_win10] cleaning build/dist contents, exe in project root
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

echo [build_win10] using:
%PIPY% -c "import sys; print(sys.executable); print(sys.version)"

%PIPY% -c "import sys; assert sys.version_info>=(3,10), 'need_310_plus'" 2>nul
if errorlevel 1 (
  echo [build_win10] FAIL: need Python 3.10 or newer
  goto :end_fail
)

%PIPY% -m pip install -q -r requirements-win10.txt
if errorlevel 1 (
  echo [build_win10] FAIL: pip install
  goto :end_fail
)

%PIPY% build.py win10
if errorlevel 1 (
  echo [build_win10] FAIL: build.py
  goto :end_fail
)

if not exist "%OUT%" (
  echo [build_win10] FAIL: missing %OUT%
  goto :end_fail
)

echo [build_win10] OK: %CD%\%OUT%
goto :end_ok

:find_python
set "PIPY="
for %%V in (3.14 3.13 3.12 3.11 3.10) do (
  where py >nul 2>&1
  if not errorlevel 1 (
    py -%%V -c "import sys; assert sys.version_info>=(3,10)" 2>nul
    if not errorlevel 1 (
      set "PIPY=py -%%V"
      goto :find_ok
    )
  )
)
where python >nul 2>&1
if not errorlevel 1 (
  python -c "import sys; assert sys.version_info>=(3,10)" 2>nul
  if not errorlevel 1 (
    set "PIPY=python"
    goto :find_ok
  )
)
where py >nul 2>&1
if not errorlevel 1 (
  py -c "import sys; assert sys.version_info>=(3,10)" 2>nul
  if not errorlevel 1 (
    set "PIPY=py"
    goto :find_ok
  )
)
echo [build_win10] FAIL: no Python 3.10+ in PATH (use py 3.10+ or python 3.10+)
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
