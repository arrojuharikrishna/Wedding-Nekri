from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.ceremonies import router as ceremony_router
from dotenv import load_dotenv

load_dotenv()
app = FastAPI(
    title="Ceremony Broadcast API",
    description="Personal live ceremony broadcasting platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this before production
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ceremony_router, prefix="/api")

@app.get("/")
def home():
    return {
        "application": "Ceremony Broadcast",
        "status": "running"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}
