import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import analytics, trades

app = FastAPI(title="pyTrade API", version="0.1.0")

origins = [o for o in os.environ.get(
    "CORS_ORIGINS", "http://localhost:4200,http://127.0.0.1:4200").split(",") if o]
# Allow the Angular dev server from any private LAN address.
LAN_REGEX = r"^http://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+)(:\d+)?$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=LAN_REGEX,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(trades.router)
app.include_router(analytics.router)
