@echo off
REM Skill wrapper for /capture - TASK-038 (Windows).
REM
REM Runs `python -m partsledger.capture` with all flags forwarded.
REM Interpreter resolution order:
REM   1. %PL_PYTHON% if set.
REM   2. The project venv at <repo>\.venv\Scripts\python.exe, if it exists.
REM   3. Plain `python` on PATH.

setlocal
set "REPO_ROOT=%~dp0..\.."
for %%I in ("%REPO_ROOT%") do set "REPO_ROOT=%%~fI"

if not "%PL_PYTHON%"=="" (
    set "PYTHON_BIN=%PL_PYTHON%"
) else if exist "%REPO_ROOT%\.venv\Scripts\python.exe" (
    set "PYTHON_BIN=%REPO_ROOT%\.venv\Scripts\python.exe"
) else (
    set "PYTHON_BIN=python"
)
"%PYTHON_BIN%" -m partsledger.capture %*
exit /b %ERRORLEVEL%
