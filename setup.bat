@echo off
rem wisland one-click setup: creates .venv, makes sure pip exists, installs requirements.
rem Works with uv (https://docs.astral.sh/uv/) as well as a regular python.org install.
rem This file is ASCII-only on purpose (cmd.exe parses .bat files with the system code page).
setlocal EnableExtensions
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
rem a stalled download should fail (and fall back to the mirror) instead of hanging forever
set "UV_HTTP_TIMEOUT=60"
set "MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple"
rem honour a mirror the user already configured for pip / uv
if defined PIP_INDEX_URL set "MIRROR=%PIP_INDEX_URL%"
if not defined PIP_INDEX_URL if defined UV_DEFAULT_INDEX set "MIRROR=%UV_DEFAULT_INDEX%"

echo.
echo  ===== wisland setup =====
echo.

rem ---- 1. find a toolchain: uv first (it can fetch its own Python), then Python 3.10+ ----
rem uv installs its interpreters under %APPDATA%\uv\python and puts a `python` shim in
rem %USERPROFILE%\.local\bin, so a machine with only uv has neither `py` nor `python`
rem on PATH. That is why uv is checked before anything else.
set "UV="
set "PY="
for /f "delims=" %%u in ('where uv 2^>nul') do if not defined UV set "UV=%%u"
if defined UV goto :have_uv

rem py launcher first, then every python.exe on PATH (the Microsoft Store stub fails the
rem version test and is skipped), then the usual install folders and uv's own pythons.
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if not errorlevel 1 for /f "delims=" %%p in ('py -3 -c "import sys; print(sys.executable)"') do set "PY=%%p"
if defined PY goto :have_py
for /f "delims=" %%p in ('where python 2^>nul') do if not defined PY call :try "%%p"
if defined PY goto :have_py
call :try "%LOCALAPPDATA%\Python\bin\python.exe"
if defined PY goto :have_py
for /d %%d in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if not defined PY call :try "%%d\python.exe"
if defined PY goto :have_py
for /d %%d in ("%ProgramFiles%\Python3*") do if not defined PY call :try "%%d\python.exe"
if defined PY goto :have_py
for /d %%d in ("%APPDATA%\uv\python\cpython-3*") do if not defined PY call :try "%%d\python.exe"
if defined PY goto :have_py

echo [x] Neither uv nor Python 3.10 or newer was found.
echo     Option A: install uv and re-run this file -^> winget install astral-sh.uv
echo     Option B: install Python from https://www.python.org/downloads/windows/
echo               and tick "Add python.exe to PATH" in the installer.
echo.
pause
exit /b 1

:have_uv
echo [1/4] Using uv: %UV%
"%UV%" --version
if exist ".venv\Scripts\python.exe" (
    echo [2/4] .venv already exists
    goto :uv_install
)
echo [2/4] Creating virtual environment .venv with uv ...
rem 3.12 / 3.13 have the widest wheel coverage (PySide6, sherpa-onnx, winrt);
rem uv downloads the interpreter if it is not installed yet. 3.14 last on purpose.
for %%v in (3.12 3.13 3.11 3.10 3.14) do if not exist ".venv\Scripts\python.exe" "%UV%" venv .venv --python %%v >nul 2>nul
if not exist ".venv\Scripts\python.exe" (
    echo [x] uv could not create .venv. Run this to see why:
    echo     uv venv .venv --python 3.12
    goto :fail
)

:uv_install
set "VPY=.venv\Scripts\python.exe"
rem uv venvs ship without pip; install it anyway so ".venv\Scripts\pip install ..." keeps working
"%VPY%" -m ensurepip --upgrade >nul 2>nul
echo [3/4] pip ready
echo [4/4] Installing dependencies with "uv pip", this can take a few minutes ...
"%UV%" pip install --python "%VPY%" -r requirements.txt
if errorlevel 1 (
    echo.
    echo [!] PyPI failed, retrying with the Tsinghua mirror ...
    "%UV%" pip install --python "%VPY%" -r requirements.txt -i %MIRROR%
    if errorlevel 1 goto :fail
)
goto :verify

:have_py
echo [1/4] Using %PY%
"%PY%" --version

rem ---- 2. virtual environment ----
if not exist ".venv\Scripts\python.exe" (
    echo [2/4] Creating virtual environment .venv ...
    "%PY%" -m venv .venv
    if errorlevel 1 goto :fail
) else (
    echo [2/4] .venv already exists
)
set "VPY=.venv\Scripts\python.exe"

rem ---- 3. pip (venvs made by uv or with --without-pip have none) ----
"%VPY%" -m pip --version >nul 2>nul
if errorlevel 1 (
    echo [3/4] pip missing, running ensurepip ...
    "%VPY%" -m ensurepip --upgrade
    if errorlevel 1 goto :fail
) else (
    echo [3/4] pip OK
)

rem ---- 4. dependencies (falls back to the Tsinghua mirror if PyPI is unreachable) ----
echo [4/4] Installing dependencies, this can take a few minutes ...
"%VPY%" -m pip install --upgrade pip >nul 2>nul
"%VPY%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [!] PyPI failed, retrying with the Tsinghua mirror ...
    "%VPY%" -m pip install -r requirements.txt -i %MIRROR%
    if errorlevel 1 goto :fail
)
goto :verify

:verify
rem make sure the packages really landed in .venv
"%VPY%" -c "import PySide6.QtWidgets, httpx, winrt.runtime" >nul 2>nul
if errorlevel 1 (
    echo.
    echo [x] Packages are still missing from .venv. Delete the .venv folder and run setup.bat again.
    goto :fail
)

echo.
echo  Done! Double-click "wisland.vbs" to start wisland.
echo  Live Japanese subtitles download their models (about 630 MB) the first time you use them.
echo.
choice /c YN /m "Start wisland now"
if errorlevel 2 exit /b 0
start "" wscript.exe "%~dp0wisland.vbs"
exit /b 0

:try
if not exist "%~1" exit /b 1
"%~1" -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set "PY=%~1"
exit /b 0

:fail
echo.
echo [x] Setup failed. Scroll up for the error message.
echo     If it is a network problem, try again later or use a proxy / mirror.
echo.
pause
exit /b 1
