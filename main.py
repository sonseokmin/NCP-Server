from fastapi import FastAPI
from routes import indexRoutes
from starlette.middleware.base import BaseHTTPMiddleware
from middlewares.logging import log

app = FastAPI()

app.add_middleware(BaseHTTPMiddleware, dispatch=log)

app.include_router(indexRoutes.router)
