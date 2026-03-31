import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.environ["BOT_TOKEN"]
GROUP_CHAT_ID: int = int(os.environ["GROUP_CHAT_ID"])
ADMIN_USER_ID: int = int(os.environ["ADMIN_USER_ID"])
TIMEZONE: str = "Asia/Singapore"
DB_PATH: str = os.path.join(os.path.dirname(__file__), "deadlines.db")
