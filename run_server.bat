@echo off
cd /d %~dp0
powershell -NoProfile -ExecutionPolicy Bypass -Command "& { .\.venv\Scripts\Activate.ps1; python manage.py runserver 0.0.0.0:8000 }"