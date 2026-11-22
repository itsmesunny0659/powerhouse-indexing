import os
import sys

# Add project root to sys.path so backend imports work seamlessly on Vercel
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.api.server import app

# Vercel Serverless looks for 'app'
