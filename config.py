from pydantic_settings import BaseSettings



class Settings(BaseSettings):
    DATABASE_URL:str
    OPENAI_API_KEY:str
    SESSION_SECRET: str
    ALGORITHM : str
    SESSION : str



    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

DATABASE_CONFIG = {
    "collection": "Scribl"
}