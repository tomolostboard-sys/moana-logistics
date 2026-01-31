from fastapi import FastAPI
from backend.app.api.v1.router import router as v1_router

app = FastAPI(title="MOANA WMS", version="0.1.0")
app.include_router(v1_router, prefix="/v1")
