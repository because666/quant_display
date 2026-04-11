"""
FastAPI 入口。亦可直接触发回测并导出静态 JSON（与 ``python -m src.backtest --run`` 等价）::

    python -m src.main --run
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.api.v1 import api_v1_router
from src.config import get_settings
from src.utils.logger import setup_logger

settings = get_settings()
logger = setup_logger(log_file=settings.log_file, log_level=settings.log_level)

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# v1 路由含健康检查、测试联调、模型预测（POST /predict、GET /model/info）等，见 src.api.v1
app.include_router(api_v1_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["system"])
def root_health_check() -> dict[str, str]:
    return {"status": "ok"}


# ==================== 前端静态文件托管 ====================
static_dir = Path(__file__).resolve().parent.parent / "static"

if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/{full_path:path}", tags=["frontend"])
    async def serve_frontend(full_path: str) -> FileResponse:
        """SPA路由兜底：所有非API路径返回index.html"""
        requested_file = static_dir / full_path
        if requested_file.exists() and requested_file.is_file():
            return FileResponse(requested_file)
        return FileResponse(static_dir / "index.html")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception at %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": str(exc), "data": None},
    )


if __name__ == "__main__":
    import sys

    if "--compare" in sys.argv[1:]:
        from src.backtest import run_comparison

        run_comparison(write_html="--no-html" not in sys.argv[1:])
        raise SystemExit(0)
    if "--run" in sys.argv[1:]:
        from src.backtest import run_backtest_and_export

        run_backtest_and_export()
        raise SystemExit(0)
