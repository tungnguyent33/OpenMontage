@echo off
rem Run the repo .venv Python with PYTHONUTF8=1 so Vietnamese output does not fail on cp1252.
rem Usage: tools_local\py.cmd <script.py | -m module> [args...]
set PYTHONUTF8=1
"%~dp0..\.venv\Scripts\python.exe" %*
