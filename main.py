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
    url = 'http://67.172.190.140:5108:5108/api/OneNote/fetch-xml-all'
    
    # هدرها
    headers = {
        'Content-Type': 'application/json; charset=utf-8',  # اینجا کلید API خود را وارد کنید
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
