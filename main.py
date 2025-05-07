from fastapi import FastAPI
import requests
from pydantic import BaseModel
from fastapi.responses import JSONResponse

# ایجاد FastAPI
app = FastAPI()

# مدل برای دریافت داده‌ها
class RequestModel(BaseModel):
    siteUrl: str
    name: str

@app.post("/api/OneNote/fetch-xml-all/")
async def fetch_xml_all(request: RequestModel):
    # آدرس API مقصد
    url = 'http://67.172.190.140:5108/api/OneNote/fetch-xml-all'
    
    # هدرها
    headers = {
        'Content-Type': 'application/json; charset=utf-8',  # اینجا کلید API خود را وارد کنید
        'sec-ch-ua-platform': 'Windows',
        'Referer': 'https://kmt.solutions-apps.com/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0',
        'sec-ch-ua': 'Chromium;v="136", "Microsoft Edge";v="136", "Not.A/Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'X-API-Key': 'your-api-key-here'  # Don't forget to add the actual API key
    }
    
    # داده‌ها
    data = {
        "siteUrl": request.siteUrl,
        "name": request.name
    }
    
    # ارسال درخواست به API
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()  # بررسی وضعیت درخواست
        return JSONResponse(content=response.json(), status_code=response.status_code)
    except requests.exceptions.RequestException as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)
