import uvicorn
import os
import sys

# Ensure current directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

if __name__ == "__main__":
    print("=" * 60)
    print("  🚀 APEXSEARCH - High-Tech Crawler & Google-Grade Indexer")
    print("=" * 60)
    print("  Local Dashboard : http://localhost:8000")
    print("  API Docs (Swagger): http://localhost:8000/docs")
    print("=" * 60)
    
    uvicorn.run("backend.api.server:app", host="127.0.0.1", port=8000, reload=True)

