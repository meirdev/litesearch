from pydantic import BaseSettings


class Settings(BaseSettings):
    DEBUG: bool

    SQLALCHEMY_DATABASE_URI: str

    SECRET_KEY: str
    ALGORITHM: str

    ADMIN_USER: str
    ADMIN_PASSWORD: str

    SERVER_HOST: str
    SERVER_PORT: int

    class Config:
        env_file = ".env"


settings = Settings()
