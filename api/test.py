import sys
import os
import traceback
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        
        diag = []
        diag.append(f"Python Version: {sys.version}")
        diag.append(f"Current Dir: {os.getcwd()}")
        diag.append(f"Files in dir: {os.listdir('.')}")
        
        # Test imports one by one
        modules_to_test = [
            "fastapi",
            "pydantic",
            "aiohttp",
            "google.auth",
            "requests",
            "jwt",
            "bs4",
            "backend.storage.db",
            "backend.crawler.spider",
            "backend.api.server"
        ]
        
        ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if ROOT_DIR not in sys.path:
            sys.path.insert(0, ROOT_DIR)
            
        for mod in modules_to_test:
            try:
                __import__(mod)
                diag.append(f"[OK] {mod}")
            except Exception as e:
                diag.append(f"[FAIL] {mod}: {e}\n{traceback.format_exc()}")
                
        self.wfile.write("\n".join(diag).encode())
