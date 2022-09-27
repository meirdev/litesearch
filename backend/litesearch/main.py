from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .router import router_index, router_token

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router_index, prefix="/indexes")
app.include_router(router_token, prefix="/auth")
