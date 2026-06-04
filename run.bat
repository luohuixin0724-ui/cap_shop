@echo off
cd /d "%~dp0"
if exist .env (
  echo 已检测到 .env，将加载 QQ 邮箱等配置
)
".venv\Scripts\python.exe" app.py
pause
