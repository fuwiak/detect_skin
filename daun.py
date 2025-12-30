import time
import requests
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("\n" + "="*50)
    print("FastAPI Server Starting")
    print("="*50)
    print("\nRegistered Routes:")
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            methods = ', '.join(sorted(route.methods))
            print(f"  {methods:20} {route.path}")
        elif hasattr(route, 'path'):
            print(f"  {'MOUNT':20} {route.path}")
    print("="*50 + "\n")
    yield
    # Shutdown (if needed)

app = FastAPI(lifespan=lifespan)

# Add request logging middleware
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        print(f"Incoming Request: {request.method} {request.url.path}")
        response = await call_next(request)
        print(f"Response: {response.status_code} for {request.method} {request.url.path}")
        return response

app.add_middleware(LoggingMiddleware)

# Add CORS middleware to allow requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURATION из переменных окружения ---
import os
import base64
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла (если есть)
load_dotenv()

ACCESS_TOKEN = os.getenv("PIXELBIN_ACCESS_TOKEN")
if not ACCESS_TOKEN:
    raise ValueError("PIXELBIN_ACCESS_TOKEN не найден в переменных окружения. Установите его в .env файле или Railway variables.")

# Convert access token to bearer token using base64 encoding
BEARER_TOKEN = base64.b64encode(ACCESS_TOKEN.encode('utf-8')).decode('utf-8')

ENDPOINT = "https://api.pixelbin.io/service/platform/transformation/v1.0/predictions/skinAnalysisInt/generate"
BASE_URL = "https://api.pixelbin.io/service/platform/transformation/v1.0/predictions"
HEADERS = {
    "Authorization": f"Bearer {BEARER_TOKEN}",
}

class PixelBinService:
    @staticmethod
    def upload_image(image_file: bytes, filename: str):
        url = ENDPOINT

        # Pixelbin requires the field name 'input.image'
        files = {
            'input.image': (filename, image_file, 'image/jpeg')
        }

        print(f"--- Attempting Upload: {filename} ---")
        print(f"URL: {url}")
        print(f"File size: {len(image_file)} bytes")

        try:
            # Don't raise for status - we'll handle errors manually
            response = requests.post(url, headers=HEADERS, files=files, timeout=30)

            # If the API returns an error (400, 401, 500), print the text!
            if not response.ok:
                print(f"API ERROR: {response.status_code}")
                print(f"RESPONSE HEADERS: {dict(response.headers)}")
                print(f"RESPONSE BODY: {response.text}")
                # Try to parse error response if it's JSON
                try:
                    error_data = response.json()
                    error_detail = f"Pixelbin Error ({response.status_code}): {error_data}"
                except:
                    error_detail = f"Pixelbin Error ({response.status_code}): {response.text}"
                # Pass the actual API error back to the frontend
                raise HTTPException(status_code=response.status_code, detail=error_detail)

            print("Upload Successful")
            result = response.json()
            print(f"Response: {result}")
            
            # Парсинг ответа
            # result содержит:
            # - _id: ID задачи для проверки статуса
            # - status: "ACCEPTED" - задача принята
            # - urls.get: URL для получения результата
            # - input.image: URL загруженного изображения
            print(f"Parsed: Job ID = {result.get('_id')}, Status = {result.get('status')}")
            
            return result

        except HTTPException:
            # Re-raise HTTP exceptions (from Pixelbin API errors)
            raise
        except requests.exceptions.RequestException as e:
            print(f"CONNECTION ERROR: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    def check_status(job_id: str):
        """
        Проверка статуса задачи по job_id
        job_id может быть либо полным ID (например, "skinAnalysisInt--generate--019afd98-...")
        либо можно использовать urls.get из ответа upload_image
        """
        # Если job_id уже полный URL, используем его, иначе формируем URL
        if job_id.startswith("http"):
            url = job_id
        else:
            url = f"{BASE_URL}/{job_id}"
            
            print(f"Checking status for job_id: {job_id}")
            print(f"URL: {url}")
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            
            if not response.ok:
                print(f"Status check error: {response.status_code}")
                print(f"Response: {response.text}")
                raise HTTPException(status_code=response.status_code, detail=response.text)
            
            result = response.json()
            print(f"Status response: {result}")
            return result
        except HTTPException:
            raise
        except Exception as e:
            print(f"Exception checking status: {e}")
            raise HTTPException(status_code=500, detail=str(e))

# API Routes - must be defined before static file mounting
@app.get("/api/test")
async def test_endpoint():
    """Test endpoint to verify API routes are working"""
    return {"status": "API is working", "message": "Routes are registered correctly"}

@app.get("/api/test-pixelbin")
async def test_pixelbin_endpoint():
    """Test endpoint to verify Pixelbin API connection and endpoint configuration"""
    test_results = {
        "endpoint": ENDPOINT,
        "bearer_token": BEARER_TOKEN[:20] + "..." if len(BEARER_TOKEN) > 20 else BEARER_TOKEN,
        "tests": []
    }
    
    # Test 1: Check if endpoint is reachable (POST without file should return error)
    try:
        response = requests.post(ENDPOINT, headers=HEADERS, timeout=10)
        test_results["tests"].append({
            "test": "POST request to endpoint",
            "status_code": response.status_code,
            "status": "success" if response.status_code in [200, 400, 422] else "unexpected",
            "response_preview": response.text[:300] if response.text else "No response body"
        })
    except requests.exceptions.RequestException as e:
        test_results["tests"].append({
            "test": "POST request to endpoint",
            "status": "error",
            "error": str(e)
        })
    
    # Test 2: Check headers configuration
    test_results["tests"].append({
        "test": "Headers configuration",
        "status": "success",
        "headers": {k: v[:20] + "..." if len(v) > 20 else v for k, v in HEADERS.items()}
    })
    
    return test_results

@app.post("/api/upload")
async def api_upload(file: UploadFile = File(...)):
    print(f"API Route Hit: Received file: {file.filename}")
    content = await file.read()
    data = PixelBinService.upload_image(content, file.filename)
    
    # Парсинг ответа и возврат структурированных данных
    return {
        "job_id": data.get("_id"),
        "status": data.get("status"),
        "urls": data.get("urls", {}),
        "input": data.get("input", {}),
        "createdAt": data.get("createdAt"),
        "retention": data.get("retention")
    }

@app.get("/api/status/{job_id}")
def api_check_status(job_id: str):
    return PixelBinService.check_status(job_id)

# Static files and root route - defined last
@app.get("/")
async def read_index():
    return FileResponse('index.html')

app.mount("/static", StaticFiles(directory="."), name="static")

if __name__ == "__main__":
    # Reload=True allows you to change code without restarting manually
    uvicorn.run("daun:app", host="0.0.0.0", port=8000, reload=True)
