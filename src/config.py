import os
from dotenv import load_dotenv

load_dotenv()

# --- Model Configs ---
EMBEDDING_MODEL_NAME = "models/gemini-embedding-001"
MODEL_NAME = "gemini-2.5-flash"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Path Configs ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(PROJECT_ROOT, "data")
RAW_DATA_PATH = os.path.join(DATA_PATH, "raw")
PROCESSED_DATA_PATH = os.path.join(DATA_PATH, "processed")

VECTOR_STORE_PATH = os.path.join(PROCESSED_DATA_PATH, "faiss_index")
SQL_DATABASE_PATH = os.path.join(PROCESSED_DATA_PATH, "metadata.db")

os.makedirs(PROCESSED_DATA_PATH, exist_ok=True)