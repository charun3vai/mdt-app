from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    app_name: str = "MDT App"
    secret_key: str = Field(default="change-me-please", description="Used for signing session cookies")
    database_url: str = "sqlite+aiosqlite:///./mdt.db"
    pdf_margin_top_mm: int = 15
    pdf_margin_right_mm: int = 15
    pdf_margin_bottom_mm: int = 15
    pdf_margin_left_mm: int = 15

settings = Settings()
