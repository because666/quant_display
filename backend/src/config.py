from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Quant Stock Ranking API"
    app_version: str = "0.1.0"
    app_env: str = "development"

    api_v1_prefix: str = "/api/v1"
    cors_allow_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    database_url: str = "sqlite:///./data/app.db"
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"

    log_level: str = "INFO"
    log_file: str = "logs/app.log"

    # 量化排序模型与因子数据路径（空字符串表示使用 backend/data、backend/models 下默认文件）
    quant_data_dir: str = Field(default="", description="factor_columns.pkl 所在目录，默认 backend/data")
    lightgbm_model_path: str = Field(default="", description="LightGBM 模型文件路径，默认 backend/models/lightgbm.pkl")
    xgboost_model_path: str = Field(default="", description="XGBoost 模型文件路径，默认 backend/models/xgboost.pkl")
    # API 默认使用的排序模型：lightgbm | xgboost
    default_predict_model: str = Field(default="lightgbm", description="默认预测模型类型")

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
