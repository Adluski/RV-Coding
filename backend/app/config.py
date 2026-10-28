import os

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./dev.db")
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-secret-change-me")
IS_PROD = os.environ.get("APP_ENV") == "production" or os.environ.get("VERCEL_ENV") == "production"
JUDGE0_URL = os.environ.get("JUDGE0_URL", "https://ce.judge0.com").rstrip("/")
JUDGE0_AUTH_TOKEN = os.environ.get("JUDGE0_AUTH_TOKEN", "")
JUDGE0_AUTH_HEADER = os.environ.get("JUDGE0_AUTH_HEADER", "X-Auth-Token")
MAX_SOURCE_BYTES = 64 * 1024
COOKIE_NAME = "session"
SESSION_DAYS = 7
# Judge0 CE language ids: Python 3.8.1 (3.11+ costs ~1.5s CPU startup on the public instance) and C++ (GCC 14.1.0, compiled with -std=c++17)
LANGUAGES = {"python": 71, "cpp": 105}
# A submission still unfinished after this long is reported as ERR.
STALE_SECONDS = 300
