import os


BASE_URL = os.getenv("BASE_URL", "localhost") 
FASTAPI_URL = f"http://{BASE_URL}:8000"