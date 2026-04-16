import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import uvicorn
from fastapi import FastAPI
from app.routes.webhook import router

logging.basicConfig(level=logging.INFO)

app = FastAPI()
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
