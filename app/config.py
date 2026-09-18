"""Configuracoes do aplicativo, carregadas do arquivo .env."""
import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    teleprompter_pin: str = os.getenv("TELEPROMPTER_PIN", "1234")
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./radar_imobiliario.db")

    # Modelo usado nas chamadas de IA
    modelo_claude: str = "claude-sonnet-5"


settings = Settings()
