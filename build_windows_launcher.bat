@echo off
setlocal
cd /d %~dp0
python build_release.py
if errorlevel 1 exit /b %errorlevel%
echo Build complete: DungeonWorld_Online_v1.0.0.exe
