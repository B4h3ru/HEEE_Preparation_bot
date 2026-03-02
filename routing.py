"""Route /start and /admin to correct handlers regardless of next_step state."""

from telebot.types import Message


def route_commands(message: Message) -> bool:
    """
    If message is /start or /admin, handle it and return True.
    Call at the start of step handlers so commands always route correctly.
    """
    text = (getattr(message, "text", None) or "").strip()
    if not text:
        return False
    # Handle /start (with optional args like /start ref123)
    if text == "/start" or text.startswith("/start "):
        from bot.handlers import handle_start
        handle_start(message)
        return True
    # Handle /admin
    if text == "/admin" or text.startswith("/admin "):
        from admin.ui_bot import handle_admin_menu
        handle_admin_menu(message)
        return True
    return False
