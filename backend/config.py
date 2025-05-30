# backend/config.py
import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Determine the path to the .env file. 
# It's typically in the project root, which is one level above the 'backend' directory.
# Or, it could be inside the 'backend' directory itself for some setups.

# Path to .env in the project root (e.g., /home/user/project/.env)
project_root_env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Path to .env directly inside the backend directory (e.g., /home/user/project/backend/.env)
backend_dir_env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '.env'))

# Try loading from project root first, then from backend directory
if os.path.exists(project_root_env_path):
    load_dotenv(dotenv_path=project_root_env_path)
    # logger.info(f"Loaded .env from project root: {project_root_env_path}")
elif os.path.exists(backend_dir_env_path):
    load_dotenv(dotenv_path=backend_dir_env_path)
    # logger.info(f"Loaded .env from backend directory: {backend_dir_env_path}")
else:
    # Fallback: load_dotenv will search in current working directory or walk up
    load_dotenv()
    # logger.warning("Attempting to load .env from default locations as it was not found in project root or backend directory.")

class Settings:
    PROJECT_NAME: str = "Real-Time Sentiment Analysis API"
    VERSION: str = "0.1.0"

    # Ollama settings
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    GRANITE_MODEL: str = os.getenv("GRANITE_MODEL", "granite")

    # Database settings
    # The default in .env.example is: postgresql+asyncpg://postgres:password@localhost:5432/sentiment_db
    DATABASE_URL: str | None = os.getenv("DATABASE_URL")

    # API general settings
    API_V1_STR: str = "/api/v1"

    def __init__(self):
        # This check can be done at instantiation to ensure critical env vars are loaded.
        if self.DATABASE_URL is None:
            logger.warning(
                "DATABASE_URL is not set in the environment. "
                "Database-dependent features will not be available. "
                "Please check your .env file or environment variables."
            )
        # else:
            # logger.info(f"DATABASE_URL successfully loaded: {self.DATABASE_URL[:self.DATABASE_URL.find('@') if '@' in self.DATABASE_URL else len(self.DATABASE_URL)]}...")

settings = Settings()

# You can add more specific checks or configurations below if needed.
# For example, ensuring the database URL has the correct scheme for asyncpg:
# if settings.DATABASE_URL and not settings.DATABASE_URL.startswith("postgresql+asyncpg"):
#     logger.warning("DATABASE_URL does not specify 'asyncpg' driver. SQLAlchemy async operations might fail.")
