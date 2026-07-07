from dotenv import load_dotenv
from pathlib import Path
import os

env_path = Path(__file__).resolve().parent / ".env"

print("Looking for:", env_path)
print("Exists:", env_path.exists())

loaded = load_dotenv(dotenv_path=env_path)

print("Loaded:", loaded)

print("HOST:", os.getenv("DATABASE_HOST"))
print("PORT:", os.getenv("DATABASE_PORT"))
print("DB:", os.getenv("DATABASE_NAME"))
print("USER:", os.getenv("DATABASE_USER"))
print("PASSWORD:", repr(os.getenv("DATABASE_PASSWORD")))