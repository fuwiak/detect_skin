import base64
import requests
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

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

# --- CONFIGURATION ---
ACCESS_TOKEN = "c5e15df7-73a6-4796-ac07-b3b6a6ccfb97"
BASE_URL = "https://api.pixelbin.io/service/platform/transformation/v1.0/predictions"

# Convert access token to bearer token using base64 encoding
BEARER_TOKEN = base64.b64encode(ACCESS_TOKEN.encode('utf-8')).decode('utf-8')

HEADERS = {
    "Authorization": f"Bearer {BEARER_TOKEN}",
}

class PixelBinService:
    @staticmethod
    def upload_image(image_file: bytes, filename: str):
        url = f"{BASE_URL}/skinAnalysisInt/generate"

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
            return result

        except HTTPException:
            # Re-raise HTTP exceptions (from Pixelbin API errors)
            raise
        except requests.exceptions.RequestException as e:
            print(f"CONNECTION ERROR: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    def check_status(job_id: str):
        url = f"{BASE_URL}/{job_id}"
        try:
            response = requests.get(url, headers=HEADERS)
            return response.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

# API Routes - must be defined before static file mounting
@app.post("/api/upload")
async def api_upload(file: UploadFile = File(...)):
    print(f"API Route Hit: Received file: {file.filename}")
    content = await file.read()
    data = PixelBinService.upload_image(content, file.filename)
    return {"job_id": data.get("_id"), "status": data.get("status")}

@app.get("/api/status/{job_id}")
def api_check_status(job_id: str):
    return PixelBinService.check_status(job_id)

@app.get("/api/test-endpoint")
def test_endpoint():
    """Тест работоспособности Pixelbin API endpoint"""
    import json
    
    results = {
        "base_url": BASE_URL,
        "endpoint": f"{BASE_URL}/skinAnalysisInt/generate",
        "tests": {}
    }
    
    # Тест 1: Проверка доступности BASE_URL
    try:
        response = requests.get(BASE_URL, headers=HEADERS, timeout=10)
        results["tests"]["base_url_available"] = {
            "status_code": response.status_code,
            "success": response.status_code in [200, 404, 405],  # 404/405 нормально для GET на POST endpoint
            "message": "Сервер доступен" if response.status_code in [200, 404, 405] else f"Неожиданный статус: {response.status_code}"
        }
    except Exception as e:
        results["tests"]["base_url_available"] = {
            "success": False,
            "error": str(e)
        }
    
    # Тест 2: Проверка структуры endpoint
    results["tests"]["endpoint_structure"] = {
        "success": True,
        "method": "POST",
        "field_name": "input.image",
        "url": f"{BASE_URL}/skinAnalysisInt/generate"
    }
    
    # Тест 3: Проверка авторизации (попытка POST без файла должна вернуть ошибку, но с правильным статусом)
    try:
        response = requests.post(f"{BASE_URL}/skinAnalysisInt/generate", headers=HEADERS, timeout=10)
        results["tests"]["authorization"] = {
            "status_code": response.status_code,
            "success": response.status_code != 401,  # 401 = не авторизован
            "message": "Авторизация работает" if response.status_code != 401 else "Ошибка авторизации"
        }
    except Exception as e:
        results["tests"]["authorization"] = {
            "success": False,
            "error": str(e)
        }
    
    return results

# Static files and root route - defined last
@app.get("/")
async def read_index():
    return FileResponse('index.html')

app.mount("/static", StaticFiles(directory="."), name="static")

@app.on_event("startup")
async def startup_event():
    """Log all registered routes on startup"""
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

if __name__ == "__main__":
    # Reload=True allows you to change code without restarting manually
    uvicorn.run("dupa:app", host="0.0.0.0", port=8000, reload=True)
