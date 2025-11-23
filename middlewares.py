# middlewares/core.py
from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging

# تنظیمات لاگ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("school_api")

class LogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"{request.client.host} - {request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s")
        return response

# تنظیمات CORS
def add_cors(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # یا لیست دامنه‌های مجاز
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# GZip برای پاسخ‌های بزرگ
def add_gzip(app):
    app.add_middleware(GZipMiddleware, minimum_size=1000)

# اضافه کردن همه middleware ها
def setup_middlewares(app):
    app.add_middleware(LogMiddleware)
    add_cors(app)
    add_gzip(app)