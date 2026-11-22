import os
import sys
import traceback

try:
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if ROOT_DIR not in sys.path:
        sys.path.insert(0, ROOT_DIR)

    from backend.api.server import app

except Exception as e:
    err_tb = traceback.format_exc()
    from fastapi import FastAPI
    from fastapi.responses import PlainTextResponse
    
    app = FastAPI()
    
    @app.api_route("/{rest_of_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    async def debug_crash_handler(rest_of_path: str):
        return PlainTextResponse(f"=== VERCEL PYTHON CRASH TRACEBACK ===\n\n{err_tb}", status_code=500)
