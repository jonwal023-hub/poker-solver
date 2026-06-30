from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Poker Solver Platform"
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/poker_solver"
    REDIS_URL: str = "redis://redis:6379/0"

    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    SOLVER_DEFAULT_ITERATIONS: int = 200
    SOLVER_VERSION: str = "1.0.0"
    SOLVER_MC_MIN_TRIALS: int = 15
    SOLVER_MC_MAX_TRIALS: int = 100

    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
