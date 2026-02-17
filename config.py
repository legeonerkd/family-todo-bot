import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set")
