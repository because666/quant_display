from fastapi import APIRouter

from .account import router as account_router
from .backtest import router as backtest_router
from .health import router as health_router
from .predict import router as predict_router
from .realtime_advice import router as realtime_advice_router
from .stockpool import router as stockpool_router
from .test import router as test_router


api_v1_router = APIRouter()
api_v1_router.include_router(health_router)
api_v1_router.include_router(test_router)
api_v1_router.include_router(predict_router)
api_v1_router.include_router(realtime_advice_router)
api_v1_router.include_router(account_router)
api_v1_router.include_router(stockpool_router)
api_v1_router.include_router(backtest_router)
