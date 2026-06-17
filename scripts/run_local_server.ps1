Set-Location -LiteralPath "F:\AI thuc chien\C2-App-091"
& ".\.venv\Scripts\python.exe" -m uvicorn src.main:app --host 127.0.0.1 --port 8000
