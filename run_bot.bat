@echo off
cd /d %~dp0
powershell -NoProfile -ExecutionPolicy Bypass -Command "& { .\.venv\Scripts\Activate.ps1; python -c \"from crm.telegram_bot import create_application; create_application().run_polling()\" }"