from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.drive_routes import drive_router  # Make sure it's FastAPI router now
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register router with /drive prefix
app.include_router(drive_router, prefix="/drive")

# Root route
@app.get("/")
async def home():
    return {"message": "✅ Framic backend is live and running!"}

@app.get("/healthz")
async def health_check():
    return {"status": "ok"}
