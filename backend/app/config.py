from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    QWEN_API_KEY: str
    QWEN_BASE_URL: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    QWEN_REASONING_MODEL: str = "qwen3.7-max"
    QWEN_EMBEDDING_MODEL: str = "text-embedding-v4"
    QWEN_RERANK_MODEL: str = "qwen3-rerank"

    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379"

    ALIBABA_ACCESS_KEY_ID: str = ""
    ALIBABA_ACCESS_KEY_SECRET: str = ""
    ALIBABA_REGION: str = "ap-southeast-1"

    MEMORY_DECAY_DEFAULT_RATE: float = 0.1
    MEMORY_IMPORTANCE_THRESHOLD: float = 0.05
    MEMORY_CONTEXT_MAX_TOKENS: int = 8000
    MEMORY_TOP_K: int = 10


settings = Settings()
