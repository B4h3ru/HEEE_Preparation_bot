from typing import Dict, Any, List

from telebot.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)

from config.settings import bot_settings
from bot_instance import bot
from routing import route_commands
from models.departments import (
    list_departments,
    create_department,
    update_department_name,
    delete_department,
)
from models.subjects import (
    list_subjects_by_department,
    create_subject,
    update_subject_name,
    delete_subject,
)
from models.questions import (
    create_question_with_options_atomic,
    list_questions_by_subject,
    get_question_with_options,
    delete_question,
    update_question_with_options_atomic,
)
from models.options import get_options_for_question
from models.users import (
    set_premium_by_username,
    list_all_telegram_ids,
    list_users_with_premium_status,
)
from models.premium_policy import set_allow_all


ADMIN_STATE: Dict[int, Dict[str, Any]] = {}

NAV_HOME = "Home"
NAV_BACK = "Back"

BTN_LIST_DEPTS = "Manage Department"
BTN_ADD_DEPT = "Add department"
BTN_LIST_categories = "Manage Category"
BTN_ADD_category = "Add Category"
BTN_ADD_QUESTION = "Add question"
BTN_MANAGE_QUESTION = "Manage Question"
BTN_SET_PREMIUM = "Set premium user"
BTN_MANAGE_USER = "Manage User"
BTN_ALLOW_ALL_USERS = "Allow ALL User"
BTN_ONLY_PREMIUM_USERS = "Only Premium User"
BTN_SEND_MAIL = "Send Mail"


def _admin_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(BTN_LIST_DEPTS), KeyboardButton(BTN_ADD_DEPT))
    kb.row(KeyboardButton(BTN_LIST_categories), KeyboardButton(BTN_ADD_category))
    kb.row(KeyboardButton(BTN_ADD_QUESTION), KeyboardButton(BTN_MANAGE_QUESTION))
    kb.row(KeyboardButton(BTN_SET_PREMIUM), KeyboardButton(BTN_MANAGE_USER))
    kb.row(KeyboardButton(BTN_ALLOW_ALL_USERS), KeyboardButton(BTN_ONLY_PREMIUM_USERS))
    kb.row(KeyboardButton(NAV_HOME), KeyboardButton(BTN_SEND_MAIL), KeyboardButton(NAV_BACK))
    return kb


def _is_admin(user_id: int) -> bool:
    return user_id in bot_settings.admin_ids


def handle_nav_buttons(message: Message) -> None:
    """Clear admin state and return to main admin menu."""
    ADMIN_STATE.pop(message.from_user.id, None)
    handle_admin_menu(message)


def _departments_keyboard(depts: List[Dict[str, Any]]) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for d in depts:
        kb.row(KeyboardButton(d["name"]))
    kb.row(KeyboardButton(NAV_HOME), KeyboardButton(NAV_BACK))
    return kb


def _categories_keyboard(dept_id: int) -> ReplyKeyboardMarkup | None:
    categories = list_subjects_by_department(dept_id)
    if not categories:
        return None
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for s in categories:
        kb.row(KeyboardButton(s["name"]))
    kb.row(KeyboardButton(NAV_HOME), KeyboardButton(NAV_BACK))
    return kb


def _nav_only_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(NAV_HOME), KeyboardButton(NAV_BACK))
    return kb


@bot.message_handler(commands=["admin"])
def handle_admin_menu(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        bot.reply_to(message, "You are not authorized to use admin commands.")
        return

    # Always switch to admin flow; clear any user state
    try:
        from bot.handlers import ACTIVE_SESSIONS
        ACTIVE_SESSIONS.pop(message.from_user.id, None)
    except ImportError:
        pass

    bot.reply_to(
        message,
        "Admin panel. Choose an action:",
        reply_markup=_admin_keyboard(),
    )


@bot.message_handler(
    func=lambda m: bool(getattr(m, "from_user", None))
    and _is_admin(m.from_user.id)
    and m.text in (NAV_HOME, NAV_BACK, BTN_SEND_MAIL)
)
def handle_nav_and_send_mail(message: Message) -> None:
    if message.text == BTN_SEND_MAIL:
        ADMIN_STATE[message.from_user.id] = {"action": "send_mail"}
        msg = bot.send_message(
            message.chat.id,
            "Send the notification message to broadcast to all bot users:",
            reply_markup=_admin_keyboard(),
        )
        bot.register_next_step_handler(msg, _handle_send_mail_message)
        return

    handle_nav_buttons(message)  # NAV_HOME or NAV_BACK


@bot.message_handler(
    func=lambda m: bool(getattr(m, "from_user", None))
    and _is_admin(m.from_user.id)
    and m.text == BTN_ALLOW_ALL_USERS
)
def handle_allow_all_users_menu(message: Message) -> None:
    user_id = message.from_user.id
    ADMIN_STATE[user_id] = {"action": "set_premium_policy", "allow_all": True}

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(
            text="✅ Confirm",
            callback_data="adm_policy_allow_all_yes",
        )
    )
    keyboard.add(InlineKeyboardButton(text="❌ Cancel", callback_data="adm_policy_cancel"))

    bot.send_message(
        message.chat.id,
        "Confirm: Allow ALL User to use premium features?",
        reply_markup=keyboard,
    )


@bot.message_handler(
    func=lambda m: bool(getattr(m, "from_user", None))
    and _is_admin(m.from_user.id)
    and m.text == BTN_ONLY_PREMIUM_USERS
)
def handle_only_premium_users_menu(message: Message) -> None:
    user_id = message.from_user.id
    ADMIN_STATE[user_id] = {"action": "set_premium_policy", "allow_all": False}

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(
            text="✅ Confirm",
            callback_data="adm_policy_only_premium_yes",
        )
    )
    keyboard.add(InlineKeyboardButton(text="❌ Cancel", callback_data="adm_policy_cancel"))

    bot.send_message(
        message.chat.id,
        "Confirm: Only Premium users can use premium features?",
        reply_markup=keyboard,
    )


@bot.callback_query_handler(
    func=lambda c: c.data
    in ("adm_policy_allow_all_yes", "adm_policy_only_premium_yes", "adm_policy_cancel")
)
def handle_premium_policy_action(call: CallbackQuery) -> None:
    if not _is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Not authorized.")
        return

    user_id = call.from_user.id
    if call.data == "adm_policy_cancel":
        ADMIN_STATE.pop(user_id, None)
        bot.answer_callback_query(call.id, "Cancelled.")
        bot.send_message(call.message.chat.id, "Cancelled.", reply_markup=_admin_keyboard())
        return

    allow_all = call.data == "adm_policy_allow_all_yes"
    set_allow_all(allow_all=allow_all)

    ADMIN_STATE.pop(user_id, None)
    bot.answer_callback_query(call.id, "Updated.")
    bot.send_message(
        call.message.chat.id,
        f"Premium policy updated: {'Allow ALL User' if allow_all else 'Only Premium User'}",
        reply_markup=_admin_keyboard(),
    )


@bot.message_handler(
    func=lambda m: bool(getattr(m, "from_user", None))
    and _is_admin(m.from_user.id)
    and m.text == BTN_MANAGE_USER
)
def handle_manage_user_menu(message: Message) -> None:
    user_id = message.from_user.id
    ADMIN_STATE[user_id] = {"action": "manage_users_menu"}

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(
            text="Show All Users",
            callback_data="adm_users_show_all",
        )
    )

    bot.send_message(
        message.chat.id,
        "Manage User. Choose an option:",
        reply_markup=keyboard,
    )


@bot.callback_query_handler(func=lambda c: c.data == "adm_users_show_all")
def handle_admin_users_show_all(call: CallbackQuery) -> None:
    if not _is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Not authorized.")
        return

    users = list_users_with_premium_status()
    if not users:
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "No users found yet.", reply_markup=_admin_keyboard())
        return

    active = [u for u in users if u.get("is_premium")]
    inactive = [u for u in users if not u.get("is_premium")]

    def _display(u: Dict[str, Any]) -> str:
        username = (u.get("username") or "").strip()
        if username:
            return f"@{username} ({u.get('telegram_id')})"
        first = (u.get("first_name") or "").strip()
        return f"{first or 'User'} ({u.get('telegram_id')})"

    max_lines = 20
    active_lines = [_display(u) for u in active[:max_lines]]
    inactive_lines = [_display(u) for u in inactive[:max_lines]]

    if len(active) > max_lines:
        active_lines.append(f"... +{len(active) - max_lines} more")
    if len(inactive) > max_lines:
        inactive_lines.append(f"... +{len(inactive) - max_lines} more")

    text = (
        f"Total users: {len(users)}\n"
        f"Active (Premium=True): {len(active)}\n\n"
        f"Active users:\n" + "\n".join(active_lines) + "\n\n"
        f"Inactive (Premium=False): {len(inactive)}\n\n"
        f"Inactive users:\n" + "\n".join(inactive_lines)
    )

    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        text,
        reply_markup=_admin_keyboard(),
    )


def _handle_send_mail_message(message: Message) -> None:
    if route_commands(message):
        return
    user_id = message.from_user.id
    state = ADMIN_STATE.get(user_id, {})
    if state.get("action") != "send_mail":
        return

    if message.text in (NAV_HOME, NAV_BACK):
        ADMIN_STATE.pop(user_id, None)
        handle_admin_menu(message)
        return

    text = (message.text or "").strip()
    if not text:
        msg = bot.send_message(
            message.chat.id,
            "Message cannot be empty. Send the notification text, or Home/Back to cancel:",
            reply_markup=_admin_keyboard(),
        )
        bot.register_next_step_handler(msg, _handle_send_mail_message)
        return

    telegram_ids = list_all_telegram_ids()
    sent = 0
    failed = 0
    for tid in telegram_ids:
        try:
            bot.send_message(tid, text)
            sent += 1
        except Exception:
            failed += 1

    ADMIN_STATE.pop(user_id, None)
    bot.reply_to(
        message,
        f"Broadcast complete.\nSent: {sent}\nFailed: {failed}\nTotal users: {len(telegram_ids)}",
        reply_markup=_admin_keyboard(),
    )


@bot.message_handler(
    func=lambda m: bool(getattr(m, "from_user", None))
    and _is_admin(m.from_user.id)
    and m.text == BTN_LIST_DEPTS
)
def handle_list_departments_menu(message: Message) -> None:
    depts = list_departments()
    if not depts:
        bot.reply_to(
            message,
            "No departments found.",
            reply_markup=_admin_keyboard(),
        )
        return
    for d in depts:
        kb = InlineKeyboardMarkup()
        kb.row(
            InlineKeyboardButton("Edit", callback_data=f"adm_dept_edit_{d['id']}"),
            InlineKeyboardButton("Delete", callback_data=f"adm_dept_del_{d['id']}"),
        )
        bot.send_message(
            message.chat.id,
            f"Department #{d['id']}: {d['name']}",
            reply_markup=kb,
        )
    bot.send_message(message.chat.id, "Department management list loaded.", reply_markup=_admin_keyboard())


@bot.message_handler(
    func=lambda m: bool(getattr(m, "from_user", None))
    and _is_admin(m.from_user.id)
    and m.text == BTN_ADD_DEPT
)
def handle_add_department_menu(message: Message) -> None:
    ADMIN_STATE[message.from_user.id] = {"action": "add_dept"}
    msg = bot.send_message(
        message.chat.id,
        "Send new department name:",
        reply_markup=_admin_keyboard(),
    )
    bot.register_next_step_handler(msg, _handle_add_department_name)


def _handle_add_department_name(message: Message) -> None:
    if route_commands(message):
        return
    user_id = message.from_user.id
    if ADMIN_STATE.get(user_id, {}).get("action") != "add_dept":
        return

    # If admin presses Home/Back while in "add department" flow, treat as navigation,
    # not as a department name.
    if message.text in (NAV_HOME, NAV_BACK):
        handle_nav_buttons(message)
        return

    name = message.text.strip()
    if not name:
        bot.reply_to(
            message,
            "Department name cannot be empty.",
            reply_markup=_admin_keyboard(),
        )
        return
    dept_id = create_department(name)
    bot.reply_to(
        message,
        f"Created department #{dept_id}: {name}",
        reply_markup=_admin_keyboard(),
    )
    ADMIN_STATE.pop(user_id, None)


@bot.message_handler(
    func=lambda m: bool(getattr(m, "from_user", None))
    and _is_admin(m.from_user.id)
    and m.text == BTN_LIST_categories
)
def handle_list_categories_menu(message: Message) -> None:
    _send_list_categories_department_keyboard(message.from_user.id, message.chat.id)


def _send_list_categories_department_keyboard(user_id: int, chat_id: int) -> None:
    depts = list_departments()
    if not depts:
        bot.send_message(
            chat_id,
            "No departments found.",
            reply_markup=_admin_keyboard(),
        )
        return

    ADMIN_STATE[user_id] = {"action": "list_categories_pick_dept"}

    kb = _departments_keyboard(depts)

    msg = bot.send_message(
        chat_id,
        "Choose department to list its categories:",
        reply_markup=kb,
    )
    bot.register_next_step_handler(msg, _handle_list_categories_pick_department)


def _handle_list_categories_pick_department(message: Message) -> None:
    if route_commands(message):
        return
    user_id = message.from_user.id
    state = ADMIN_STATE.get(user_id, {})
    if state.get("action") != "list_categories_pick_dept":
        return

    if message.text in (NAV_HOME, NAV_BACK):
        handle_nav_buttons(message)
        return

    chosen_name = message.text.strip()
    depts = list_departments()
    dept = next((d for d in depts if d["name"] == chosen_name), None)
    if not dept:
        bot.reply_to(message, "Unknown department. Please choose one of the listed buttons.")
        _send_list_categories_department_keyboard(user_id, message.chat.id)
        return

    dept_id = dept["id"]

    categories = list_subjects_by_department(dept_id)
    if not categories:
        bot.reply_to(
            message,
            "No categories for this department.",
            reply_markup=_admin_keyboard(),
        )
        return
    for c in categories:
        kb = InlineKeyboardMarkup()
        kb.row(
            InlineKeyboardButton("Edit", callback_data=f"adm_cat_edit_{c['id']}"),
            InlineKeyboardButton("Delete", callback_data=f"adm_cat_del_{c['id']}"),
        )
        bot.send_message(
            message.chat.id,
            f"Category #{c['id']}: {c['name']}",
            reply_markup=kb,
        )
    bot.send_message(message.chat.id, "Category management list loaded.", reply_markup=_admin_keyboard())
    # Stay in manage-category flow: show department choices again.
    _send_list_categories_department_keyboard(user_id, message.chat.id)


@bot.message_handler(
    func=lambda m: bool(getattr(m, "from_user", None))
    and _is_admin(m.from_user.id)
    and m.text == BTN_ADD_category
)
def handle_add_category_menu(message: Message) -> None:
    _send_add_category_department_keyboard(message.from_user.id, message.chat.id)


def _send_add_category_department_keyboard(user_id: int, chat_id: int) -> None:
    depts = list_departments()
    if not depts:
        bot.send_message(
            chat_id,
            "No departments found. Create a department first.",
            reply_markup=_admin_keyboard(),
        )
        return

    ADMIN_STATE[user_id] = {"action": "add_category_pick_dept"}

    kb = _departments_keyboard(depts)

    msg = bot.send_message(
        chat_id,
        "Choose department for new category:",
        reply_markup=kb,
    )
    bot.register_next_step_handler(msg, _handle_add_category_pick_department)


def _handle_add_category_pick_department(message: Message) -> None:
    if route_commands(message):
        return
    user_id = message.from_user.id
    state = ADMIN_STATE.get(user_id, {})
    if state.get("action") != "add_category_pick_dept":
        return

    if message.text in (NAV_HOME, NAV_BACK):
        handle_nav_buttons(message)
        return

    chosen_name = message.text.strip()
    depts = list_departments()
    dept = next((d for d in depts if d["name"] == chosen_name), None)
    if not dept:
        bot.reply_to(message, "Unknown department. Please choose one of the listed buttons.")
        _send_add_category_department_keyboard(user_id, message.chat.id)
        return

    state["department_id"] = dept["id"]
    state["department_name"] = dept["name"]
    state["action"] = "add_category_name"
    ADMIN_STATE[user_id] = state

    dept_kb = _departments_keyboard(depts)
    msg = bot.send_message(
        message.chat.id,
        f"Send category name for department '{dept['name']}':",
        reply_markup=dept_kb,
    )
    bot.register_next_step_handler(msg, _handle_add_category_name)


def _handle_add_category_name(message: Message) -> None:
    if route_commands(message):
        return
    user_id = message.from_user.id
    state = ADMIN_STATE.get(user_id, {})
    if state.get("action") != "add_category_name":
        return

    if message.text in (NAV_HOME, NAV_BACK):
        handle_nav_buttons(message)
        return

    depts = list_departments()
    dept_kb = _departments_keyboard(depts) if depts else _admin_keyboard()

    # If admin taps a department button while we're asking for category name,
    # treat it as switching the target department (not as a category name).
    chosen_as_dept = next((d for d in depts if d["name"] == (message.text or "").strip()), None)
    if chosen_as_dept:
        state["department_id"] = chosen_as_dept["id"]
        state["department_name"] = chosen_as_dept["name"]
        ADMIN_STATE[user_id] = state
        msg = bot.send_message(
            message.chat.id,
            f"Switched to department '{chosen_as_dept['name']}'. Now send category name:",
            reply_markup=dept_kb,
        )
        bot.register_next_step_handler(msg, _handle_add_category_name)
        return

    dept_id = state.get("department_id")
    dept_name = state.get("department_name", "")
    name = message.text.strip()
    if not name:
        msg = bot.send_message(
            message.chat.id,
            "category name cannot be empty. Send category name:",
            reply_markup=dept_kb,
        )
        bot.register_next_step_handler(msg, _handle_add_category_name)
        return

    subj_id = create_subject(dept_id, name)
    bot.reply_to(
        message,
        f"Created category #{subj_id} in department '{dept_name or dept_id}': {name}",
        reply_markup=dept_kb,
    )
    # Stay in add-category flow for same department; ask for another category.
    msg = bot.send_message(
        message.chat.id,
        f"Send another category name for department '{dept_name or dept_id}', "
        f"or use Home/Back to exit.",
        reply_markup=dept_kb,
    )
    bot.register_next_step_handler(msg, _handle_add_category_name)


@bot.message_handler(
    func=lambda m: bool(getattr(m, "from_user", None))
    and _is_admin(m.from_user.id)
    and m.text == BTN_MANAGE_QUESTION
)
def handle_manage_question_menu(message: Message) -> None:
    _send_manage_question_department_keyboard(message.from_user.id, message.chat.id)


def _send_manage_question_department_keyboard(user_id: int, chat_id: int) -> None:
    depts = list_departments()
    if not depts:
        bot.send_message(
            chat_id,
            "No departments found.",
            reply_markup=_admin_keyboard(),
        )
        return
    ADMIN_STATE[user_id] = {"action": "manage_question_pick_dept"}
    kb = _departments_keyboard(depts)
    msg = bot.send_message(
        chat_id,
        "Choose department to manage questions:",
        reply_markup=kb,
    )
    bot.register_next_step_handler(msg, _handle_manage_question_pick_department)


def _handle_manage_question_pick_department(message: Message) -> None:
    if route_commands(message):
        return
    user_id = message.from_user.id
    state = ADMIN_STATE.get(user_id, {})
    if state.get("action") != "manage_question_pick_dept":
        return
    if message.text in (NAV_HOME, NAV_BACK):
        handle_nav_buttons(message)
        return
    chosen_name = message.text.strip()
    depts = list_departments()
    dept = next((d for d in depts if d["name"] == chosen_name), None)
    if not dept:
        bot.reply_to(message, "Unknown department. Choose one of the listed buttons.")
        _send_manage_question_department_keyboard(user_id, message.chat.id)
        return
    state["department_id"] = dept["id"]
    state["department_name"] = dept["name"]
    state["action"] = "manage_question_pick_category"
    ADMIN_STATE[user_id] = state
    _send_manage_question_category_keyboard(user_id, message.chat.id)


def _send_manage_question_category_keyboard(user_id: int, chat_id: int) -> None:
    state = ADMIN_STATE.get(user_id, {})
    dept_id = state.get("department_id")
    dept_name = state.get("department_name", "")
    kb = _categories_keyboard(dept_id)
    if kb is None:
        bot.send_message(
            chat_id,
            f"No categories in department '{dept_name or dept_id}'.",
            reply_markup=_admin_keyboard(),
        )
        ADMIN_STATE.pop(user_id, None)
        return
    msg = bot.send_message(
        chat_id,
        f"Choose category to manage questions in '{dept_name or dept_id}':",
        reply_markup=kb,
    )
    bot.register_next_step_handler(msg, _handle_manage_question_pick_category)


def _handle_manage_question_pick_category(message: Message) -> None:
    if route_commands(message):
        return
    user_id = message.from_user.id
    state = ADMIN_STATE.get(user_id, {})
    if state.get("action") != "manage_question_pick_category":
        return
    if message.text in (NAV_HOME, NAV_BACK):
        handle_nav_buttons(message)
        return
    dept_id = state.get("department_id")
    chosen_name = message.text.strip()
    categories = list_subjects_by_department(dept_id)
    category = next((s for s in categories if s["name"] == chosen_name), None)
    if not category:
        bot.reply_to(message, "Unknown category. Choose one of the listed buttons.")
        _send_manage_question_category_keyboard(user_id, message.chat.id)
        return

    category_id = category["id"]
    category_name = category["name"]
    questions = list_questions_by_subject(category_id)
    ADMIN_STATE.pop(user_id, None)
    if not questions:
        bot.reply_to(
            message,
            f"No questions in category '{category_name}'.",
            reply_markup=_admin_keyboard(),
        )
        return
    for q in questions:
        opts = get_options_for_question(q["id"])
        lines = [f"Q{q['id']}: {q['question_text']}"]
        for i, o in enumerate(opts, 1):
            mark = " ✓" if o.get("is_correct") else ""
            lines.append(f"  {i}. {o['option_text']}{mark}")
        text = "\n".join(lines)
        if len(text) > 4000:
            text = text[:3997] + "..."
        kb = InlineKeyboardMarkup()
        kb.row(
            InlineKeyboardButton("Delete", callback_data=f"adm_q_del_{q['id']}"),
            InlineKeyboardButton("Edit", callback_data=f"adm_q_edit_{q['id']}"),
        )
        bot.send_message(message.chat.id, text, reply_markup=kb, parse_mode="")
    bot.send_message(
        message.chat.id,
        f"Done. {len(questions)} question(s). Use Home/Back or Manage Question again.",
        reply_markup=_admin_keyboard(),
    )


@bot.message_handler(
    func=lambda m: bool(getattr(m, "from_user", None))
    and _is_admin(m.from_user.id)
    and m.text == BTN_ADD_QUESTION
)
def handle_add_question_menu(message: Message) -> None:
    _send_add_question_department_keyboard(message.from_user.id, message.chat.id)


def _send_add_question_department_keyboard(user_id: int, chat_id: int) -> None:
    depts = list_departments()
    if not depts:
        bot.send_message(
            chat_id,
            "No departments found. Create a department first.",
            reply_markup=_admin_keyboard(),
        )
        return

    ADMIN_STATE[user_id] = {"action": "add_question_pick_dept"}

    kb = _departments_keyboard(depts)
    msg = bot.send_message(
        chat_id,
        "Choose department for new question:",
        reply_markup=kb,
    )
    bot.register_next_step_handler(msg, _handle_add_question_pick_department)


def _handle_add_question_pick_department(message: Message) -> None:
    if route_commands(message):
        return
    user_id = message.from_user.id
    state = ADMIN_STATE.get(user_id, {})
    if state.get("action") != "add_question_pick_dept":
        return

    if message.text in (NAV_HOME, NAV_BACK):
        handle_nav_buttons(message)
        return

    chosen_name = message.text.strip()
    depts = list_departments()
    dept = next((d for d in depts if d["name"] == chosen_name), None)
    if not dept:
        bot.reply_to(message, "Unknown department. Please choose one of the listed buttons.")
        _send_add_question_department_keyboard(user_id, message.chat.id)
        return

    state["department_id"] = dept["id"]
    state["department_name"] = dept["name"]
    state["action"] = "add_question_pick_category"
    ADMIN_STATE[user_id] = state

    _send_add_question_category_keyboard(user_id, message.chat.id)


def _send_add_question_category_keyboard(user_id: int, chat_id: int) -> None:
    state = ADMIN_STATE.get(user_id, {})
    dept_id = state.get("department_id")
    dept_name = state.get("department_name", "")
    kb = _categories_keyboard(dept_id)
    if kb is None:
        bot.send_message(
            chat_id,
            f"No categories found in department '{dept_name or dept_id}'. "
            f"Create a category first.",
            reply_markup=_admin_keyboard(),
        )
        return

    msg = bot.send_message(
        chat_id,
        f"Choose category for new question in department '{dept_name or dept_id}':",
        reply_markup=kb,
    )
    bot.register_next_step_handler(msg, _handle_add_question_pick_category)


def _handle_add_question_pick_category(message: Message) -> None:
    if route_commands(message):
        return
    user_id = message.from_user.id
    state = ADMIN_STATE.get(user_id, {})
    if state.get("action") != "add_question_pick_category":
        return

    if message.text in (NAV_HOME, NAV_BACK):
        handle_nav_buttons(message)
        return

    dept_id = state.get("department_id")
    dept_name = state.get("department_name", "")
    chosen_name = message.text.strip()
    categories = list_subjects_by_department(dept_id)
    subj = next((s for s in categories if s["name"] == chosen_name), None)
    if not subj:
        bot.reply_to(message, "Unknown category. Please choose one of the listed buttons.")
        _send_add_question_category_keyboard(user_id, message.chat.id)
        return

    state["category_id"] = subj["id"]
    state["category_name"] = subj["name"]
    state["action"] = "add_question_text"
    ADMIN_STATE[user_id] = state

    kb = _nav_only_keyboard()
    msg = bot.send_message(
        message.chat.id,
        f"Send question text for category '{subj['name']}' "
        f"in department '{dept_name or dept_id}':",
        reply_markup=kb,
    )
    bot.register_next_step_handler(msg, _handle_add_question_text)


def _handle_add_question_text(message: Message) -> None:
    if route_commands(message):
        return
    user_id = message.from_user.id
    state = ADMIN_STATE.get(user_id, {})
    if state.get("action") != "add_question_text":
        return

    if message.text in (NAV_HOME, NAV_BACK):
        handle_nav_buttons(message)
        return

    text = message.text.strip()
    if not text:
        msg = bot.send_message(
            message.chat.id,
            "Question text cannot be empty. Send question text:",
            reply_markup=_nav_only_keyboard(),
        )
        bot.register_next_step_handler(msg, _handle_add_question_text)
        return

    state["question_text"] = text
    state["action"] = "add_question_explanation"
    ADMIN_STATE[user_id] = state
    msg = bot.send_message(
        message.chat.id,
        "Send explanation text (or '-' to skip):",
        reply_markup=_nav_only_keyboard(),
    )
    bot.register_next_step_handler(msg, _handle_add_question_explanation)


def _handle_add_question_explanation(message: Message) -> None:
    if route_commands(message):
        return
    user_id = message.from_user.id
    state = ADMIN_STATE.get(user_id, {})
    if state.get("action") != "add_question_explanation":
        return

    if message.text in (NAV_HOME, NAV_BACK):
        handle_nav_buttons(message)
        return

    expl = message.text.strip()
    if expl == "-" or expl == "":
        expl = None

    state["explanation"] = expl
    state["action"] = "add_question_options"
    ADMIN_STATE[user_id] = state
    msg = bot.send_message(
        message.chat.id,
        "Send options separated by newline.\n"
        "Mark the correct option with a leading * (e.g. '*4').",
        reply_markup=_nav_only_keyboard(),
    )
    bot.register_next_step_handler(msg, _handle_add_question_options)


def _handle_add_question_options(message: Message) -> None:
    if route_commands(message):
        return
    user_id = message.from_user.id
    state = ADMIN_STATE.get(user_id, {})
    if state.get("action") != "add_question_options":
        return

    if message.text in (NAV_HOME, NAV_BACK):
        handle_nav_buttons(message)
        return

    lines = [l.strip() for l in message.text.splitlines() if l.strip()]
    if len(lines) != 4:
        msg = bot.send_message(
            message.chat.id,
            "Please send exactly 4 options (one per line).",
            reply_markup=_nav_only_keyboard(),
        )
        bot.register_next_step_handler(msg, _handle_add_question_options)
        return

    options: List[str] = []
    correct_index = None
    correct_count = 0
    for idx, line in enumerate(lines):
        if line.startswith("*"):
            text = line.lstrip("*").strip()
            if not text:
                msg = bot.send_message(
                    message.chat.id,
                    "Option text cannot be empty.",
                    reply_markup=_nav_only_keyboard(),
                )
                bot.register_next_step_handler(msg, _handle_add_question_options)
                return
            options.append(text)
            correct_count += 1
            if correct_index is None:
                correct_index = idx
        else:
            if not line:
                msg = bot.send_message(
                    message.chat.id,
                    "Option text cannot be empty.",
                    reply_markup=_nav_only_keyboard(),
                )
                bot.register_next_step_handler(msg, _handle_add_question_options)
                return
            options.append(line)

    if correct_count != 1 or correct_index is None:
        msg = bot.send_message(
            message.chat.id,
            "Mark exactly one correct option using '*'.",
            reply_markup=_nav_only_keyboard(),
        )
        bot.register_next_step_handler(msg, _handle_add_question_options)
        return

    dept_id = state["department_id"]
    subj_id = state["category_id"]
    question_text = state["question_text"]
    explanation = state.get("explanation")

    try:
        question_id = create_question_with_options_atomic(
            department_id=dept_id,
            subject_id=subj_id,
            question_text=question_text,
            explanation=explanation,
            options=options,
            correct_index=correct_index,
        )
    except Exception:
        msg = bot.send_message(
            message.chat.id,
            "Failed to save question and options. Nothing was saved. Please try again.",
            reply_markup=_nav_only_keyboard(),
        )
        bot.register_next_step_handler(msg, _handle_add_question_options)
        return

    bot.reply_to(
        message,
        f"Created question #{question_id} with {len(options)} options "
        f"(correct option index: {correct_index + 1}).",
        reply_markup=_nav_only_keyboard(),
    )

    # Keep department/category context and continue adding questions
    # until the admin presses Home/Back.
    state["action"] = "add_question_text"
    ADMIN_STATE[user_id] = state
    subj_name = state.get("category_name", "")
    dept_id_display = state.get("department_name") or dept_id
    prompt = (
        f"Send next question text for category '{subj_name}' "
        f"in department '{dept_id_display}', or use Home/Back to exit."
    )
    msg = bot.send_message(
        message.chat.id,
        prompt,
        reply_markup=_nav_only_keyboard(),
    )
    bot.register_next_step_handler(msg, _handle_add_question_text)


@bot.message_handler(
    func=lambda m: bool(getattr(m, "from_user", None))
    and _is_admin(m.from_user.id)
    and m.text == BTN_SET_PREMIUM
)
def handle_set_premium_menu(message: Message) -> None:
    ADMIN_STATE[message.from_user.id] = {"action": "set_premium_username"}
    msg = bot.send_message(
        message.chat.id,
        "Send Telegram username of the user (with or without @):",
        reply_markup=_admin_keyboard(),
    )
    bot.register_next_step_handler(msg, _handle_set_premium_username)


def _handle_set_premium_username(message: Message) -> None:
    if route_commands(message):
        return
    user_id = message.from_user.id
    state = ADMIN_STATE.get(user_id, {})
    if state.get("action") != "set_premium_username":
        return

    text = (message.text or "").strip()
    if text in (NAV_HOME, NAV_BACK):
        handle_nav_buttons(message)
        return

    username = text.lstrip("@")
    if not username:
        msg = bot.send_message(
            message.chat.id,
            "Username cannot be empty. Send Telegram username:",
            reply_markup=_admin_keyboard(),
        )
        bot.register_next_step_handler(msg, _handle_set_premium_username)
        return

    state["username"] = username
    ADMIN_STATE[user_id] = state

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(
            text="Add Premium",
            callback_data=f"adm_premium_add_{username}",
        )
    )
    keyboard.add(
        InlineKeyboardButton(
            text="Remove Premium",
            callback_data=f"adm_premium_remove_{username}",
        )
    )

    bot.send_message(
        message.chat.id,
        f"User: @{username}\nChoose premium action:",
        reply_markup=keyboard,
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_premium_"))
def handle_premium_action(call: CallbackQuery) -> None:
    parts = call.data.split("_", 3)
    if len(parts) != 4:
        bot.answer_callback_query(call.id, "Invalid action.")
        return

    _, _, action, username = parts
    is_premium = action == "add"

    affected = set_premium_by_username(username, is_premium)
    if affected == 0:
        text = f"No user found with username '@{username}'."
    else:
        text = (
            f"Premium status for '@{username}' updated: "
            f"is_premium = {is_premium}."
        )

    ADMIN_STATE.pop(call.from_user.id, None)
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, text, reply_markup=_admin_keyboard())


@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_q_del_"))
def handle_admin_question_delete(call: CallbackQuery) -> None:
    if not _is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Not authorized.")
        return
    try:
        qid = int(call.data.replace("adm_q_del_", ""))
    except ValueError:
        bot.answer_callback_query(call.id, "Invalid question.")
        return
    deleted = delete_question(qid)
    bot.answer_callback_query(call.id, "Deleted." if deleted else "Not found.")
    new_text = (call.message.text or "Question") + "\n\nDeleted."
    try:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=new_text,
            reply_markup=None,
        )
    except Exception:
        pass


@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_q_edit_"))
def handle_admin_question_edit_start(call: CallbackQuery) -> None:
    if not _is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Not authorized.")
        return
    try:
        qid = int(call.data.replace("adm_q_edit_", ""))
    except ValueError:
        bot.answer_callback_query(call.id, "Invalid question.")
        return
    data = get_question_with_options(qid)
    if not data:
        bot.answer_callback_query(call.id, "Question not found.")
        return
    opts = data.get("options") or []
    try:
        correct_index = next(i for i, o in enumerate(opts) if o.get("is_correct"))
    except StopIteration:
        correct_index = 0
    bot.answer_callback_query(call.id)
    ADMIN_STATE[call.from_user.id] = {
        "action": "edit_question_text",
        "question_id": qid,
        "current_text": data["question_text"],
        "current_explanation": data["explanation"] or "",
        "current_options": [o["option_text"] for o in opts],
        "correct_index": correct_index,
    }
    msg = bot.send_message(
        call.message.chat.id,
        f"Send new question text (or '-' to keep current):\nCurrent: {data['question_text'][:150]}{'…' if len(data['question_text']) > 150 else ''}",
        reply_markup=_nav_only_keyboard(),
        parse_mode="",
    )
    bot.register_next_step_handler(msg, _handle_edit_question_text)


def _handle_edit_question_text(message: Message) -> None:
    if route_commands(message):
        return
    user_id = message.from_user.id
    state = ADMIN_STATE.get(user_id, {})
    if state.get("action") != "edit_question_text":
        return
    if message.text in (NAV_HOME, NAV_BACK):
        ADMIN_STATE.pop(user_id, None)
        handle_admin_menu(message)
        return
    new_text = message.text.strip()
    if new_text == "-" or not new_text:
        state["question_text"] = state["current_text"]
    else:
        state["question_text"] = new_text
    state["action"] = "edit_question_explanation"
    ADMIN_STATE[user_id] = state
    current = (state.get("current_explanation") or "")[:100]
    msg = bot.send_message(
        message.chat.id,
        f"Send new explanation (or '-' to keep current):\nCurrent: {current}{'…' if len(state.get('current_explanation') or '') > 100 else ''}",
        reply_markup=_nav_only_keyboard(),
        parse_mode="",
    )
    bot.register_next_step_handler(msg, _handle_edit_question_explanation)


def _handle_edit_question_explanation(message: Message) -> None:
    if route_commands(message):
        return
    user_id = message.from_user.id
    state = ADMIN_STATE.get(user_id, {})
    if state.get("action") != "edit_question_explanation":
        return
    if message.text in (NAV_HOME, NAV_BACK):
        ADMIN_STATE.pop(user_id, None)
        handle_admin_menu(message)
        return
    new_expl = message.text.strip()
    if new_expl == "-" or not new_expl:
        state["explanation"] = state.get("current_explanation") or None
    else:
        state["explanation"] = new_expl
    state["action"] = "edit_question_options"
    ADMIN_STATE[user_id] = state
    opts = state.get("current_options") or []
    current_preview = "\n".join(
        f"  {i+1}. {t[:50]}…" if len(t) > 50 else f"  {i+1}. {t}"
        for i, t in enumerate(opts)
    )
    msg = bot.send_message(
        message.chat.id,
        "Send 4 options, one per line. Mark correct with leading * (e.g. '*4').\nCurrent:\n"
        + (current_preview or "(none)"),
        reply_markup=_nav_only_keyboard(),
        parse_mode="",
    )
    bot.register_next_step_handler(msg, _handle_edit_question_options)


def _handle_edit_question_options(message: Message) -> None:
    if route_commands(message):
        return
    user_id = message.from_user.id
    state = ADMIN_STATE.get(user_id, {})
    if state.get("action") != "edit_question_options":
        return
    if message.text in (NAV_HOME, NAV_BACK):
        ADMIN_STATE.pop(user_id, None)
        handle_admin_menu(message)
        return
    lines = [l.strip() for l in message.text.splitlines() if l.strip()]
    if len(lines) != 4:
        msg = bot.send_message(
            message.chat.id,
            "Send exactly 4 options (one per line). One must be marked with *.",
            reply_markup=_nav_only_keyboard(),
        )
        bot.register_next_step_handler(msg, _handle_edit_question_options)
        return
    options: List[str] = []
    correct_index = None
    correct_count = 0
    for idx, line in enumerate(lines):
        if line.startswith("*"):
            text = line.lstrip("*").strip()
            if not text:
                msg = bot.send_message(
                    message.chat.id,
                    "Option text cannot be empty.",
                    reply_markup=_nav_only_keyboard(),
                )
                bot.register_next_step_handler(msg, _handle_edit_question_options)
                return
            options.append(text)
            correct_count += 1
            if correct_index is None:
                correct_index = idx
        else:
            options.append(line)
    if correct_count != 1 or correct_index is None:
        msg = bot.send_message(
            message.chat.id,
            "Mark exactly one correct option with '*'.",
            reply_markup=_nav_only_keyboard(),
        )
        bot.register_next_step_handler(msg, _handle_edit_question_options)
        return
    qid = state["question_id"]
    try:
        update_question_with_options_atomic(
            question_id=qid,
            question_text=state["question_text"],
            explanation=state.get("explanation"),
            options=options,
            correct_index=correct_index,
        )
    except Exception:
        bot.send_message(
            message.chat.id,
            "Update failed. Please try again.",
            reply_markup=_admin_keyboard(),
        )
        ADMIN_STATE.pop(user_id, None)
        return
    ADMIN_STATE.pop(user_id, None)
    bot.reply_to(
        message,
        f"Question #{qid} updated.",
        reply_markup=_admin_keyboard(),
    )


@bot.callback_query_handler(
    func=lambda c: c.data.startswith("adm_dept_edit_") or c.data.startswith("adm_dept_del_")
)
def handle_department_manage_actions(call: CallbackQuery) -> None:
    if not _is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Not authorized.")
        return

    if call.data.startswith("adm_dept_del_"):
        dept_id = int(call.data.replace("adm_dept_del_", ""))
        affected = delete_department(dept_id)
        bot.answer_callback_query(call.id, "Deleted." if affected else "Not found.")
        bot.send_message(
            call.message.chat.id,
            f"Department #{dept_id} {'deleted' if affected else 'not found'}.",
            reply_markup=_admin_keyboard(),
        )
        return

    dept_id = int(call.data.replace("adm_dept_edit_", ""))
    ADMIN_STATE[call.from_user.id] = {"action": "edit_department_name", "department_id": dept_id}
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        f"Send new name for Department #{dept_id}:",
        reply_markup=_admin_keyboard(),
    )
    bot.register_next_step_handler(msg, _handle_edit_department_name)


def _handle_edit_department_name(message: Message) -> None:
    if route_commands(message):
        return
    state = ADMIN_STATE.get(message.from_user.id, {})
    if state.get("action") != "edit_department_name":
        return
    if message.text in (NAV_HOME, NAV_BACK):
        handle_nav_buttons(message)
        return

    new_name = (message.text or "").strip()
    if not new_name:
        msg = bot.send_message(message.chat.id, "Department name cannot be empty.", reply_markup=_admin_keyboard())
        bot.register_next_step_handler(msg, _handle_edit_department_name)
        return

    dept_id = state["department_id"]
    affected = update_department_name(dept_id, new_name)
    ADMIN_STATE.pop(message.from_user.id, None)
    bot.send_message(
        message.chat.id,
        f"Department #{dept_id} {'updated' if affected else 'not found'}.",
        reply_markup=_admin_keyboard(),
    )


@bot.callback_query_handler(
    func=lambda c: c.data.startswith("adm_cat_edit_") or c.data.startswith("adm_cat_del_")
)
def handle_category_manage_actions(call: CallbackQuery) -> None:
    if not _is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Not authorized.")
        return

    if call.data.startswith("adm_cat_del_"):
        cat_id = int(call.data.replace("adm_cat_del_", ""))
        affected = delete_subject(cat_id)
        bot.answer_callback_query(call.id, "Deleted." if affected else "Not found.")
        bot.send_message(
            call.message.chat.id,
            f"Category #{cat_id} {'deleted' if affected else 'not found'}.",
            reply_markup=_admin_keyboard(),
        )
        return

    cat_id = int(call.data.replace("adm_cat_edit_", ""))
    ADMIN_STATE[call.from_user.id] = {"action": "edit_category_name", "category_id": cat_id}
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        f"Send new name for Category #{cat_id}:",
        reply_markup=_admin_keyboard(),
    )
    bot.register_next_step_handler(msg, _handle_edit_category_name)


def _handle_edit_category_name(message: Message) -> None:
    if route_commands(message):
        return
    state = ADMIN_STATE.get(message.from_user.id, {})
    if state.get("action") != "edit_category_name":
        return
    if message.text in (NAV_HOME, NAV_BACK):
        handle_nav_buttons(message)
        return

    new_name = (message.text or "").strip()
    if not new_name:
        msg = bot.send_message(message.chat.id, "Category name cannot be empty.", reply_markup=_admin_keyboard())
        bot.register_next_step_handler(msg, _handle_edit_category_name)
        return

    cat_id = state["category_id"]
    affected = update_subject_name(cat_id, new_name)
    ADMIN_STATE.pop(message.from_user.id, None)
    bot.send_message(
        message.chat.id,
        f"Category #{cat_id} {'updated' if affected else 'not found'}.",
        reply_markup=_admin_keyboard(),
    )
