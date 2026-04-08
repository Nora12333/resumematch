from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

from routers.analyze import router as analyze_router
from routers.generate import router as generate_router


app = FastAPI(title="ResumeMatch API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze_router)
app.include_router(generate_router)


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}
