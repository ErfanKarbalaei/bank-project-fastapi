# app/core/config.py

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- JWT Config ---
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- Database Config ---
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASS: str

    @property
    def database_url(self) -> str:
        """
        URL اتصال برای Alembic و SQLAlchemy-compatible.
        این URL را دست نمی‌زنیم تا Alembic به کار خود ادامه دهد.
        """
        return (
            f"postgresql://"
            f"{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def asyncpg_url(self) -> str:
        """
        URL اتصال مستقیم برای asyncpg (بدون درایور).
        ما از این در session.py استفاده خواهیم کرد.
        """
        return (
            f"postgresql://"
            f"{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()