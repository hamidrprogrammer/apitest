from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
from pydantic import BaseModel
from fastapi.responses import JSONResponse

# ایجاد FastAPI
app = FastAPI()

# اضافه کردن CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # یا می‌توانید به‌جای "*" دامنه‌های مجاز را لیست کنید، مثلاً: ["https://example.com"]
    allow_credentials=True,
    allow_methods=["*"],  # تمام متدها (GET, POST, PUT, DELETE, ...) مجاز هستند
    allow_headers=["*"],  # تمام هدرها مجاز هستند
)

# مدل برای دریافت داده‌ها
class RequestModel(BaseModel):
    siteUrl: str
    name: str
class RequestModelID(BaseModel):
    id: str
    title: str
@app.post("/api/OneNote/fetch-xml-all-id/")
async def fetch_xml_all(request: RequestModelID):
    # آدرس API مقصد
    url = 'http://67.172.190.140:5108/api/OneNote/fetch-xml-all-id'
    
    # هدرها
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'sec-ch-ua-platform': 'Windows',
        'Referer': 'https://kmt.solutions-apps.com/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0',
        'sec-ch-ua': 'Chromium;v="136", "Microsoft Edge";v="136", "Not.A/Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'X-API-Key': 'your-api-key-here'
    }
    
    # داده‌ها
    data = {
        "id": request.id,
        "title": request.title
    }
    
    # ارسال درخواست به API
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return JSONResponse(content=response.json(), status_code=response.status_code)
    except requests.exceptions.RequestException as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)    

@app.post("/api/OneNote/fetch-xml-all/")
async def fetch_xml_all(request: RequestModel):
    # آدرس API مقصد
    url = 'http://67.172.190.140:5108/api/OneNote/fetch-xml-all'
    
    # هدرها
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'sec-ch-ua-platform': 'Windows',
        'Referer': 'https://kmt.solutions-apps.com/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0',
        'sec-ch-ua': 'Chromium;v="136", "Microsoft Edge";v="136", "Not.A/Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'X-API-Key': 'your-api-key-here'
    }
    
    # داده‌ها
    data = {
        "siteUrl": request.siteUrl,
        "name": request.name
    }
    
    # ارسال درخواست به API
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return JSONResponse(content=response.json(), status_code=response.status_code)
    except requests.exceptions.RequestException as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)
