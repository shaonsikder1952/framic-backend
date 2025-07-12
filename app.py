from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from routes.drive_routes import drive_router
from dotenv import load_dotenv
import os
import logging

load_dotenv()
logger = logging.getLogger("App")

app = FastAPI()

# Add rate limiter to app state
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Register the global rate limit exception handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(f"🚫 Rate limit exceeded: {request.client.host}")
    return _rate_limit_exceeded_handler(request, exc)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register the drive router
app.include_router(drive_router, prefix="/drive")

@app.get("/")
async def home():
    return {"message": "✅ Framic backend is live and running!"}

@app.get("/healthz")
async def health_check():
    return {"status": "ok"}
