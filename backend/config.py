from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    app_env: str = "development"
    enable_debug_endpoints: bool = True
    database_url: str = f"sqlite:///{(ROOT / 'data' / 'admissions.db').as_posix()}"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    miniprogram_origin: str = "*"
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        origins = [origin.strip() for origin in self.miniprogram_origin.split(",") if origin.strip()]
        return origins or ["*"]

    @property
    def debug_endpoints_enabled(self) -> bool:
        return self.enable_debug_endpoints and self.app_env.lower() != "production"


settings = Settings()
