from __future__ import annotations

import json
import logging
import pathlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from app.api.routers.views_router import router as views_router
from app.api.routers.portfolios_router import router as portfolios_router
from app.api.routers.bl_router import router as bl_router
from app.api.routers.news_router import router as news_router
from app.api.routers.backtest_router import router as backtest_router
from app.api.routers.agent_router import router as agent_router
from app.api.routers.admin_router import router as admin_router
from app.db.database import init_db, seed_portfolios

MOCK_PATH = (
    pathlib.Path(__file__).resolve().parents[3]
    / "frontend" / "bl_main" / "src" / "features" / "bl_main" / "mock" / "mockBlMainData.json"
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if MOCK_PATH.exists():
        mock = json.loads(MOCK_PATH.read_text(encoding="utf-8"))
        seed_portfolios(mock.get("portfolios", []))
    yield


app = FastAPI(title="Portfolio Backtesting API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(views_router)
app.include_router(portfolios_router)
app.include_router(bl_router)
app.include_router(news_router)
app.include_router(backtest_router)
app.include_router(agent_router)
app.include_router(admin_router)
