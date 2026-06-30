@echo off
cd /d D:\Python\finops-ai\backend
call venv\Scripts\activate.bat
python -m uvicorn app.main:app --reload