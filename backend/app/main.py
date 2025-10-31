import json
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.database import Base, engine
from app.models import *  # noqa: F401,F403
from app.routers import auth, data_items, files, fluorescence, log_entries, projects, subjects, tags, user_projects, users
from app.utils.logger import api_logger as logger

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SCI Platform API",
    description="Scientific Data Management Platform for Neuroscience Research",
    version="1.0.0"
)


class WrapResponseMiddleware(BaseHTTPMiddleware):
    """统一响应格式中间件"""
    
    # 预编译排除路径集合，提高性能
    EXCLUDED_PATHS = {"/docs", "/openapi.json", "/redoc"}
    
    async def dispatch(self, request, call_next):
        path = request.url.path
        
        # 优化路径检查：使用集合查找或前缀匹配
        if path in self.EXCLUDED_PATHS or path.startswith(("/docs", "/openapi", "/redoc")):
            return await call_next(request)

        logger.debug(f"Request: {request.method} {path}")
        response = await call_next(request)
        content_type = response.headers.get("content-type", "")
        
        # 非 JSON 响应直接返回（如文件下载）
        if "application/json" not in content_type:
            return response

        # 读取响应体 - 优化内存使用
        body_chunks = []
        async for chunk in response.body_iterator:
            body_chunks.append(chunk)
        body = b"".join(body_chunks)

        background = response.background
        
        # 空响应体处理
        if not body:
            wrapped = {"code": 0, "data": None, "message": ""}
            return JSONResponse(
                content=wrapped,
                status_code=response.status_code,
                background=background,
            )
        
        try:
            data = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
                background=background,
            )
        except UnicodeDecodeError as e:
            logger.error(f"Unicode decode error: {e}")
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
                background=background,
            )

        # 移除会导致问题的响应头
        headers = {
            key: value
            for key, value in dict(response.headers).items()
            if key.lower() not in ("content-length", "transfer-encoding")
        }

        # 如果已经是包装格式，直接返回
        if isinstance(data, dict) and {"code", "data", "message"}.issubset(data.keys()):
            return JSONResponse(
                content=data,
                status_code=response.status_code,
                headers=headers,
                background=background,
            )

        # 错误响应包装
        if response.status_code >= 400:
            message = ""
            payload = None
            if isinstance(data, dict) and "detail" in data:
                message = data.get("detail", "")
            else:
                payload = data
            wrapped = {"code": response.status_code, "data": payload, "message": message}
            logger.warning(f"Error response: {response.status_code} - {message}")
            return JSONResponse(
                content=wrapped,
                status_code=response.status_code,
                headers=headers,
                background=background,
            )

        # 成功响应包装
        wrapped = {"code": 0, "data": data, "message": ""}
        return JSONResponse(
            content=wrapped,
            status_code=response.status_code,
            headers=headers,
            background=background,
        )


# CORS 配置（允许前端访问）
# 从环境变量读取允许的来源，默认为开发环境
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5666,http://localhost:5173,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],  # 允许前端访问下载文件名
    max_age=3600,  # 预检请求缓存时间（秒）
)

# 响应包装中间件
app.add_middleware(WrapResponseMiddleware)

API_PREFIX = "/api"

# 注册所有路由
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)
app.include_router(projects.router, prefix=API_PREFIX)
app.include_router(subjects.router, prefix=API_PREFIX)
app.include_router(data_items.router, prefix=API_PREFIX)
app.include_router(files.router, prefix=API_PREFIX)
app.include_router(fluorescence.router, prefix=API_PREFIX)
app.include_router(tags.router, prefix=API_PREFIX)
app.include_router(log_entries.router, prefix=API_PREFIX)
app.include_router(user_projects.router, prefix=API_PREFIX)


@app.get("/")
def root():
    """健康检查端点"""
    logger.info("Health check requested")
    return {"message": "SCI Platform API is running", "version": "1.0.0"}


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("=" * 50)
    logger.info("SCI Platform API Starting...")
    logger.info(f"API Version: 1.0.0")
    logger.info(f"API Prefix: {API_PREFIX}")
    logger.info("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("SCI Platform API Shutting down...")
