import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.environ["BOT_TOKEN"]
GROUP_CHAT_ID: int = int(os.environ["GROUP_CHAT_ID"])
ADMIN_USER_ID: int = int(os.environ["ADMIN_USER_ID"])
DATABASE_URL: str = os.environ["DATABASE_URL"]
TIMEZONE: str = "Asia/Singapore"
