"""
Rafiq Backend — Main Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import router

app = FastAPI(
    title="رفيق (Rafiq) — Medical AI Backend",
    description="Backend API for the Rafiq personal health assistant powered by Mado AI agents.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — adjust origins as needed for your mobile/web client
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/", tags=["Health"])
async def health_check():
    return {"status": "Rafiq is running 🚀", "version": "1.0.0"}
