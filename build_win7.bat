@echo off
setlocal EnableExtensions
cd /d "%~dp0"
for %%I in ("%~dp0.") do set "BM_ROOT=%%~fI"

set "OUT=bm-windows-on-top_win7.exe"
set "PYI_DIST=dist"
set "PYI_WORK=build"
set "PYI_SPEC=."

echo [build_win7] Build Win7+tkinter: %OUT%
echo [build_win7] cleaning build/dist contents, exe in project root
taskkill /F /IM "%OUT%" /T >nul 2>&1
if not exist "build" mkdir "build" 2>nul
if not exist "dist" mkdir "dist" 2>nul
call :clean_dir_contents "build"
call :clean_dir_contents "dist"
if exist "bm-windows-on-top.spec" del /f /q "bm-windows-on-top.spec" 2>nul
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

%PIPY% gen_icons.py
if not exist "icons\icon.ico" (
  echo [build_win7] FAIL: no icons\icon.ico (pip install pillow^)
  goto :end_fail
)

if not exist "wav\switch.wav" (
  echo [build_win7] FAIL: no wav\switch.wav ^(provide fixed shared wav file^)
  goto :end_fail
)

%PIPY% -m PyInstaller --noconfirm --clean --noconsole --onefile --name "bm-windows-on-top_win7" --distpath "%PYI_DIST%" --workpath "%PYI_WORK%" --specpath "%PYI_SPEC%" --icon="%BM_ROOT%\icons\icon.ico" --version-file "%BM_ROOT%\version_info.txt" --hidden-import "pystray" --hidden-import "keyboard" --add-data "%BM_ROOT%\icons;icons" --add-data "%BM_ROOT%\wav;wav" "%BM_ROOT%\main.py"
if errorlevel 1 (
  echo [build_win7] FAIL: PyInstaller
  goto :end_fail
)

if not exist "%PYI_DIST%\%OUT%" (
  echo [build_win7] FAIL: missing %OUT% in %PYI_DIST%
  goto :end_fail
)

move /y "%PYI_DIST%\%OUT%" "%OUT%" >nul
if errorlevel 1 (
  echo [build_win7] FAIL: move output to project root
  goto :end_fail
)

if not exist "%OUT%" (
  echo [build_win7] FAIL: missing %OUT% after move
  goto :end_fail
)

call :clean_dir_contents "build"
call :clean_dir_contents "dist"

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
