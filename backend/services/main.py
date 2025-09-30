# backend/services/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers.adcopy import router as adcopy_router

app = FastAPI(title="Poster API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(adcopy_router)

@app.get("/")
def root():
    return {"ok": True, "msg": "Poster API running"}