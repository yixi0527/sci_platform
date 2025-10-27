import json

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.database import Base, engine
from app.models import *  # noqa: F401,F403
from app.routers import auth, data_items, files, log_entries, projects, subjects, tags, user_projects, users

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SCI Platform API")


class WrapResponseMiddleware(BaseHTTPMiddleware):
	async def dispatch(self, request, call_next):
		path = request.url.path
		if path.startswith("/docs") or path.startswith("/openapi") or path.startswith("/redoc"):
			return await call_next(request)

		response = await call_next(request)
		content_type = response.headers.get("content-type", "")
		if "application/json" not in content_type:
			return response

		body = b""
		async for chunk in response.body_iterator:
			body += chunk

		background = response.background
		try:
			data = json.loads(body.decode()) if body else None
		except json.JSONDecodeError:
			return Response(
				content=body,
				status_code=response.status_code,
				headers=dict(response.headers),
				media_type=response.media_type,
				background=background,
			)

		headers = {
			key: value
			for key, value in dict(response.headers).items()
			if key.lower() not in ("content-length", "transfer-encoding")
		}

		if isinstance(data, dict) and {"code", "data", "message"}.issubset(data.keys()):
			return JSONResponse(
				content=data,
				status_code=response.status_code,
				headers=headers,
				background=background,
			)

		if response.status_code >= 400:
			message = ""
			payload = None
			if isinstance(data, dict) and "detail" in data:
				message = data.get("detail", "")
			else:
				payload = data
			wrapped = {"code": response.status_code, "data": payload, "message": message}
			return JSONResponse(
				content=wrapped,
				status_code=response.status_code,
				headers=headers,
				background=background,
			)

		wrapped = {"code": 0, "data": data, "message": ""}
		return JSONResponse(
			content=wrapped,
			status_code=response.status_code,
			headers=headers,
			background=background,
		)


app.add_middleware(WrapResponseMiddleware)

API_PREFIX = "/api"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)
app.include_router(projects.router, prefix=API_PREFIX)
app.include_router(subjects.router, prefix=API_PREFIX)
app.include_router(data_items.router, prefix=API_PREFIX)
app.include_router(files.router, prefix=API_PREFIX)
app.include_router(tags.router, prefix=API_PREFIX)
app.include_router(log_entries.router, prefix=API_PREFIX)
app.include_router(user_projects.router, prefix=API_PREFIX)


@app.get("/")
def root():
	return {"message": "SCI Platform backend running"}
