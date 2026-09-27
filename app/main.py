from fastapi import FastAPI

from app.api.router import router

app = FastAPI(title="LLM Security Evaluation Service")
app.include_router(router)
