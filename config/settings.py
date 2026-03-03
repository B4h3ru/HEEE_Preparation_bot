import os
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv


load_dotenv()


@dataclass
class BotSettings:
    token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    admin_ids: List[int] = field(
        default_factory=lambda: [
            int(x)
            for x in os.getenv("ADMIN_TELEGRAM_IDS", "").split(",")
            if x.strip().isdigit()
        ]
    )
    required_channel: str = os.getenv("REQUIRED_CHANNEL", "HEEE_Preparation")


@dataclass
class DBSettings:
    host: str = os.getenv("DB_HOST", "localhost").strip()
    port: int = int(os.getenv("DB_PORT", "3306"))
    name: str = os.getenv("DB_NAME", "heee_bot").strip()
    user: str = os.getenv("DB_USER", "root").strip()
    password: str = os.getenv("DB_PASSWORD", "")


bot_settings = BotSettings()
db_settings = DBSettings()
