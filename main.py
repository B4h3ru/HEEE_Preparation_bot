import admin.ui_bot  # noqa: F401  # registers admin handlers (first, so they have priority)
import bot.handlers  # noqa: F401  # registers user handlers (catch-all is last)

from bot_instance import bot


def main() -> None:
    print("Starting HEEE Preparation Bot (User + Admin)...")
    bot.infinity_polling()


if __name__ == "__main__":
    main()
