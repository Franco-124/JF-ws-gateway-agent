import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.routes.webhook import router
from scheduler import build_scheduler

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = build_scheduler()
    scheduler.start()
    logging.getLogger(__name__).info("Scheduler started.")
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        logging.getLogger(__name__).info("Scheduler stopped.")


app = FastAPI(lifespan=lifespan)
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
