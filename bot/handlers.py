from typing import Dict

from telebot.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

from config.settings import bot_settings
from bot_instance import bot
from routing import route_commands
from models.users import get_or_create_user, is_user_premium
from models.departments import list_departments
from models.subjects import list_subjects_by_department
from models.questions import get_random_questions
from models.options import get_options_for_question
from models.sessions import (
    create_quiz_session,
    add_session_questions,
    save_answer,
    update_score,
    get_session_summary,
    has_free_10_attempt,
)


ACTIVE_SESSIONS: Dict[int, Dict] = {}

NAV_HOME = "🏠 Home"
NAV_BACK = "🔙 Back"
BTN_SUB_PREMIUM = "💰 Subscribe Premium 💰"
BTN_RANDOM_10 = "🎲 Random 10 Questions"
BTN_RANDOM_50 = "🎲 Random 50 Questions"
BTN_RANDOM_100 = "100 Questions"


def _departments_keyboard() -> ReplyKeyboardMarkup:
    depts = list_departments()
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    if depts:
        for i in range(0, len(depts), 2):
            row = [KeyboardButton(depts[i]["name"])]
            if i + 1 < len(depts):
                row.append(KeyboardButton(depts[i + 1]["name"]))
            kb.row(*row)
    kb.row(KeyboardButton(BTN_SUB_PREMIUM))
    kb.row(KeyboardButton(NAV_HOME), KeyboardButton(NAV_BACK))
    return kb


def _subjects_keyboard(department_id: int) -> ReplyKeyboardMarkup | None:
    subjects = list_subjects_by_department(department_id)
    if not subjects:
        return None
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for s in subjects:
        kb.row(KeyboardButton(s["name"]))
    kb.row(KeyboardButton(BTN_SUB_PREMIUM))
    kb.row(KeyboardButton(NAV_HOME), KeyboardButton(NAV_BACK))
    return kb


def _quiz_type_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(BTN_RANDOM_10))
    kb.row(KeyboardButton(BTN_RANDOM_50))
    kb.row(KeyboardButton(BTN_RANDOM_100))
    kb.row(KeyboardButton(BTN_SUB_PREMIUM))
    kb.row(KeyboardButton(NAV_HOME), KeyboardButton(NAV_BACK))
    return kb


def _quiz_nav_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(NAV_HOME), KeyboardButton(NAV_BACK))
    return kb


def _send_premium_info(chat_id: int) -> None:
    text = (
        "To subscribe to Premium:\n"
        "1) Send the subscription fee 100-Birr to account:\n\n"
        "   Bank: Telebirr\n"
        "   Account: 0914370474\n"
        "   Name: Bahiru Walelign\n   ---------------------------\n\n"
        
        "   Bank: CBE\n"
        "   Account: 1000315929109\n"
        "   Name: Bahiru Walelign\n   ---------------------------\n\n"
        
        "   Bank: Awash Bank \n"
        "   Account: 013201583556600\n"
        "   Name: Bahiru Walelign\n   ---------------------------\n\n"
        
        "   Bank: Bank of Abyssinia (BOA)\n"
        "   Account: 98812601\n"
        "   Name: Bahiru Walelign\n   ---------------------------\n\n"
        
        "2) After payment, send the receipt and your Telegram username "
        "to our support: @HEEE_Prep_Support_service\n\n\n"
        "We will activate your premium access as soon as we verify the payment."
    )
    bot.send_message(chat_id, text)


REQUIRED_CHANNEL_MSG = (
    "📢 Join Required!\n\n"
    "ይሄን ቦት ለመጠቀም እባክዎ መጀመሪያ ቻናላችንን ይቀላቀሉ😊\n"
    "join ካደረጉ በኋላ ✅Check Membership የሚለውን ይንኩት\n\n"
    "To continue using the bot, please join our channel:\n\n"
    "https://t.me/{channel}\n\n"
    "After joining, click 'Check Membership'."
)


def _is_channel_member(chat_id: str, user_id: int) -> bool:
    """Check if user is a member of the channel. Bot must be admin in channel."""
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False


def _join_channel_keyboard() -> InlineKeyboardMarkup:
    channel = bot_settings.required_channel.lstrip("@")
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(text="Join Channel", url=f"https://t.me/{channel}"))
    kb.add(InlineKeyboardButton(text="✅ Check Membership", callback_data="check_membership"))
    return kb


def _show_join_required(chat_id: int, telegram_id: int) -> None:
    """Show join channel message with inline buttons."""
    channel = bot_settings.required_channel.lstrip("@")
    text = REQUIRED_CHANNEL_MSG.format(channel=channel)
    bot.send_message(chat_id, text, reply_markup=_join_channel_keyboard())


def _show_departments(chat_id: int, telegram_id: int, show_welcome: bool = True) -> None:
    kb = _departments_keyboard()
    depts = list_departments()
    state = ACTIVE_SESSIONS.get(telegram_id, {})
    state["step"] = "choose_department"
    ACTIVE_SESSIONS[telegram_id] = state

    if not depts:
        text = (
            "No departments configured yet.\n"
            "Please contact an admin or check back later.\n\n"
            "Use Subscribe Premium to learn about premium features."
        )
    elif show_welcome:
        username = state.get("username") or ""
        display_name = username or "Student"
        text = (
            f"Hello, Dear @{display_name}! Welcome to HEEE(Higher Education Exit Exam) Preparation Bot!\n\n"
            "ይሄ ቦት እያለ የ Exit Exam ነገር በጭራሽ ሊያሳስቦት አይገባም ።ይህን ያውቃሉ? ደጋግሞ ከማጥናት በላይ አዕምሮዋችን የተጠየቀውን ነገር ነው ማይረሳው።\n\n"
            "እዚ ቦት ላይ በሺዎች የሚቆጠሩ ጥያቄዎችን ከነ መልስና ማብራሪያው አዘጋጅተናል። \n\nመልካም እድል😊 \n\n"
            "Please choose your department and start practicing 👇"
        )
    else:
        text = "Please choose your department and start practicing 👇"

    msg = bot.send_message(chat_id, text, reply_markup=kb)
    bot.register_next_step_handler(msg, handle_department_select_text)


def _show_subjects(chat_id: int, telegram_id: int) -> None:
    state = ACTIVE_SESSIONS.get(telegram_id, {})
    department_id = state.get("department_id")
    department_name = state.get("department_name", "")
    kb = _subjects_keyboard(department_id)
    if kb is None:
        bot.send_message(chat_id, "No subjects for this department. Returning to home.")
        # Clear department context and go back to departments list
        state.pop("department_id", None)
        state.pop("department_name", None)
        ACTIVE_SESSIONS[telegram_id] = state
        _show_departments(chat_id, telegram_id, show_welcome=False)
        return
    state["step"] = "choose_subject"
    ACTIVE_SESSIONS[telegram_id] = state
    msg = bot.send_message(
        chat_id,
        f"Department: {department_name or department_id}\nChoose a subject:",
        reply_markup=kb,
    )
    bot.register_next_step_handler(msg, handle_subject_select_text)


@bot.message_handler(
    func=lambda m: ACTIVE_SESSIONS.get(m.from_user.id, {}).get("step") == "in_quiz"
    and (m.text or "").strip() in (NAV_HOME, NAV_BACK)
)
def handle_nav_during_quiz(message: Message) -> None:
    telegram_id = message.from_user.id
    state = ACTIVE_SESSIONS.get(telegram_id)
    if not state:
        bot.reply_to(message, "Session expired. Send /start again.")
        return

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(
            text="Yes, cancel session",
            callback_data="cancel_quiz_yes",
        ),
        InlineKeyboardButton(
            text="No, continue",
            callback_data="cancel_quiz_no",
        ),
    )
    bot.send_message(
        message.chat.id,
        "You are in the middle of a practice session.\n"
        "Do you want to cancel this session and go back to the subject list?",
        reply_markup=keyboard,
    )


@bot.message_handler(commands=["start"])
def handle_start(message: Message) -> None:
    # Always switch to user flow; clear any admin state
    try:
        from admin.ui_bot import ADMIN_STATE
        ADMIN_STATE.pop(message.from_user.id, None)
    except ImportError:
        pass

    telegram_user = message.from_user
    user_id = get_or_create_user(
        telegram_id=telegram_user.id,
        username=telegram_user.username,
        first_name=telegram_user.first_name,
        last_name=telegram_user.last_name,
    )

    display_username = telegram_user.username or telegram_user.first_name or ""
    ACTIVE_SESSIONS[telegram_user.id] = {
        "db_user_id": user_id,
        "username": display_username,
    }
    _show_join_required(message.chat.id, telegram_user.id)


def handle_department_select_text(message: Message) -> None:
    if route_commands(message):
        return
    telegram_id = message.from_user.id
    state = ACTIVE_SESSIONS.get(telegram_id, {})
    db_user_id = state.get("db_user_id")
    if not db_user_id:
        bot.reply_to(message, "Session expired. Send /start again.")
        return

    text = (message.text or "").strip()

    if text == BTN_SUB_PREMIUM:
        _send_premium_info(message.chat.id)
        _show_departments(message.chat.id, telegram_id, show_welcome=False)
        return

    if text in (NAV_HOME, NAV_BACK):
        _show_departments(message.chat.id, telegram_id, show_welcome=False)
        return

    departments = list_departments()
    dept = next((d for d in departments if d["name"] == text), None)
    if not dept:
        kb = _departments_keyboard()
        msg = bot.reply_to(
            message,
            "Unknown department. Please tap one of the buttons.",
            reply_markup=kb,
        )
        bot.register_next_step_handler(msg, handle_department_select_text)
        return

    department_id = dept["id"]
    state.update({"department_id": department_id, "department_name": dept["name"]})
    ACTIVE_SESSIONS[telegram_id] = state

    _show_subjects(message.chat.id, telegram_id)


def handle_subject_select_text(message: Message) -> None:
    if route_commands(message):
        return
    telegram_id = message.from_user.id
    state = ACTIVE_SESSIONS.get(telegram_id, {})
    db_user_id = state.get("db_user_id")
    department_id = state.get("department_id")
    if not db_user_id or not department_id:
        bot.reply_to(message, "Session expired. Send /start again.")
        return

    text = (message.text or "").strip()

    if text == BTN_SUB_PREMIUM:
        _send_premium_info(message.chat.id)
        _show_subjects(message.chat.id, telegram_id)  # No welcome (subjects list)
        return

    if text == NAV_HOME:
        # Reset and go back to departments list
        state.pop("department_id", None)
        state.pop("department_name", None)
        ACTIVE_SESSIONS[telegram_id] = state
        _show_departments(message.chat.id, telegram_id, show_welcome=False)
        return

    if text == NAV_BACK:
        # Back to departments list
        _show_departments(message.chat.id, telegram_id, show_welcome=False)
        return

    subjects = list_subjects_by_department(department_id)
    subj = next((s for s in subjects if s["name"] == text), None)
    if not subj:
        kb = _subjects_keyboard(department_id)
        msg = bot.reply_to(
            message,
            "Unknown subject. Please tap one of the buttons.",
            reply_markup=kb,
        )
        bot.register_next_step_handler(msg, handle_subject_select_text)
        return

    subject_id = subj["id"]

    state.update(
        {
            "subject_id": subject_id,
            "subject_name": subj["name"],
            "step": "choose_quiz_type",
        }
    )
    ACTIVE_SESSIONS[telegram_id] = state

    kb = _quiz_type_keyboard()
    msg = bot.reply_to(
        message,
        f"Subject: {subj['name']}\nChoose practice mode:",
        reply_markup=kb,
    )
    bot.register_next_step_handler(msg, handle_quiz_type_select)


def handle_quiz_type_select(message: Message) -> None:
    if route_commands(message):
        return
    telegram_id = message.from_user.id
    state = ACTIVE_SESSIONS.get(telegram_id, {})
    db_user_id = state.get("db_user_id")
    department_id = state.get("department_id")
    subject_id = state.get("subject_id")
    if not db_user_id or not department_id or not subject_id:
        bot.reply_to(message, "Session expired. Send /start again.")
        return

    text = (message.text or "").strip()

    if text == BTN_SUB_PREMIUM:
        _send_premium_info(message.chat.id)
        kb = _quiz_type_keyboard()
        msg = bot.reply_to(
            message,
            "Choose practice mode:",
            reply_markup=kb,
        )
        bot.register_next_step_handler(msg, handle_quiz_type_select)
        return

    if text == NAV_HOME:
        # Reset and go back to departments list
        for key in ("department_id", "department_name", "subject_id", "subject_name"):
            state.pop(key, None)
        ACTIVE_SESSIONS[telegram_id] = state
        _show_departments(message.chat.id, telegram_id, show_welcome=False)
        return

    if text == NAV_BACK:
        # Back to subject list in same department
        state.pop("subject_id", None)
        state.pop("subject_name", None)
        ACTIVE_SESSIONS[telegram_id] = state
        _show_subjects(message.chat.id, telegram_id)
        return

    is_premium = is_user_premium(db_user_id)

    if text == BTN_RANDOM_10:
        # One-time free attempt for non-premium users.
        if (not is_premium) and has_free_10_attempt(db_user_id):
            _send_premium_info(message.chat.id)
            kb = _quiz_type_keyboard()
            msg = bot.reply_to(
                message,
                "Free 10-question attempt used. Subscribe to continue:",
                reply_markup=kb,
            )
            bot.register_next_step_handler(msg, handle_quiz_type_select)
            return
        wanted = 10
    elif text in (BTN_RANDOM_50, BTN_RANDOM_100):
        if not is_premium:
            _send_premium_info(message.chat.id)
            kb = _quiz_type_keyboard()
            msg = bot.reply_to(
                message,
                "Choose a practice mode (Premium required for bove 10 questions):",
                reply_markup=kb,
            )
            bot.register_next_step_handler(msg, handle_quiz_type_select)
            return
        wanted = 50 if text == BTN_RANDOM_50 else 100
    else:
        kb = _quiz_type_keyboard()
        msg = bot.reply_to(
            message,
            "Please choose one of the practice modes.",
            reply_markup=kb,
        )
        bot.register_next_step_handler(msg, handle_quiz_type_select)
        return

    questions = get_random_questions(department_id, subject_id, wanted)
    if not questions:
        bot.reply_to(
            message,
            "No questions for this subject. Please choose another subject.",
        )
        _show_subjects(message.chat.id, telegram_id)
        return

    session_id = create_quiz_session(
        db_user_id,
        department_id,
        subject_id,
        len(questions),
    )
    question_ids = [q["id"] for q in questions]
    add_session_questions(session_id, question_ids)

    ACTIVE_SESSIONS[telegram_id].update(
        {
            "session_id": session_id,
            "questions": questions,
            "current_index": 0,
            "step": "in_quiz",
        }
    )

    # While in a question session, show only Home/Back navigation buttons.
    bot.send_message(
        message.chat.id,
        "Practice session started. Use the buttons below to go Home or Back.",
        reply_markup=_quiz_nav_keyboard(),
    )

    send_current_question(message.chat.id, telegram_id)


def send_current_question(chat_id: int, telegram_id: int) -> None:
    state = ACTIVE_SESSIONS.get(telegram_id)
    if not state:
        return
    index = state.get("current_index", 0)
    questions = state.get("questions", [])
    if index >= len(questions):
        session_id = state.get("session_id")
        if session_id:
            update_score(session_id)
            summary = get_session_summary(session_id)
            bot.send_message(
                chat_id,
                f"Quiz finished!\nScore: {summary.get('score', 0)}/{summary.get('total_questions', 0)}",
            )
        # Clear quiz-specific state but keep department context,
        # then go back to subject list.
        for key in ("session_id", "questions", "current_index"):
            state.pop(key, None)
        state["step"] = "choose_subject"
        ACTIVE_SESSIONS[telegram_id] = state
        _show_subjects(chat_id, telegram_id)
        return

    question = questions[index]
    options = get_options_for_question(question["id"])

    labels = ["A", "B", "C", "D", "E", "F"]
    labels = labels[: len(options)]

    text_lines = [
        f"Question {index + 1}/{len(questions)}",
        "",
        question["question_text"],
        "",
    ]
    for label, opt in zip(labels, options):
        text_lines.append(f"{label}) {opt['option_text']}")

    keyboard = InlineKeyboardMarkup()
    for label, opt in zip(labels, options):
        keyboard.add(
            InlineKeyboardButton(
                text=label,
                callback_data=f"ans_{question['id']}_{opt['id']}_{label}",
            )
        )

    bot.send_message(
        chat_id,
        "\n".join(text_lines),
        reply_markup=keyboard,
    )


@bot.callback_query_handler(func=lambda c: c.data == "check_membership")
def handle_check_membership(call: CallbackQuery) -> None:
    """Verify user joined the required channel, then show departments or ask again."""
    telegram_id = call.from_user.id
    state = ACTIVE_SESSIONS.get(telegram_id)
    if not state:
        bot.answer_callback_query(call.id, "Session expired. Send /start again.")
        return

    channel = f"@{bot_settings.required_channel.lstrip('@')}"
    if _is_channel_member(channel, telegram_id):
        bot.answer_callback_query(call.id, "Welcome! You can now use the bot.")
        state["channel_verified"] = True
        ACTIVE_SESSIONS[telegram_id] = state
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        _show_departments(call.message.chat.id, telegram_id)
    else:
        bot.answer_callback_query(call.id, "Please join the channel first.")
        try:
            bot.edit_message_text(
                REQUIRED_CHANNEL_MSG.format(channel=bot_settings.required_channel.lstrip("@")),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=_join_channel_keyboard(),
            )
        except Exception:
            _show_join_required(call.message.chat.id, telegram_id)


@bot.callback_query_handler(func=lambda c: c.data.startswith("ans_"))
def handle_answer(call: CallbackQuery) -> None:
    telegram_id = call.from_user.id
    state = ACTIVE_SESSIONS.get(telegram_id)
    if not state:
        bot.answer_callback_query(call.id, "Session expired. Send /start again.")
        return

    parts = call.data.split("_", 3)
    _, qid_str, opt_id_str, selected_label = parts
    question_id = int(qid_str)
    selected_option_id = int(opt_id_str)

    options = get_options_for_question(question_id)
    is_correct = False
    correct_label = ""
    correct_text = ""
    labels = ["A", "B", "C", "D", "E", "F"]
    labels = labels[: len(options)]
    for label, opt in zip(labels, options):
        if opt["id"] == selected_option_id:
            is_correct = bool(opt["is_correct"])
        if opt["is_correct"]:
            correct_label = label
            correct_text = opt["option_text"]

    save_answer(
        session_id=state["session_id"],
        question_id=question_id,
        selected_option_id=selected_option_id,
        is_correct=is_correct,
    )

    state["current_index"] = state.get("current_index", 0) + 1
    ACTIVE_SESSIONS[telegram_id] = state

    # Find question and explanation
    question = next(
        (q for q in state.get("questions", []) if q["id"] == question_id),
        None,
    )
    explanation = ""
    if question:
        explanation = (question.get("explanation") or "").strip()

    if is_correct:
        header = "✅ Correct."
    else:
        header = "❌ Incorrect."

    body_lines = [
        header,
        f"Answer: {correct_label}) {correct_text}",
    ]
    if explanation:
        body_lines.append("")
        body_lines.append("Explanation:")
        body_lines.append(explanation)

    feedback_text = "\n".join(body_lines)

    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="Next", callback_data=f"next_{question_id}"))

    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, feedback_text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda c: c.data.startswith("next_"))
def handle_next_question(call: CallbackQuery) -> None:
    telegram_id = call.from_user.id
    state = ACTIVE_SESSIONS.get(telegram_id)
    if not state:
        bot.answer_callback_query(call.id, "Session expired. Send /start again.")
        return

    bot.answer_callback_query(call.id)
    send_current_question(call.message.chat.id, telegram_id)


@bot.callback_query_handler(
    func=lambda c: c.data in ("cancel_quiz_yes", "cancel_quiz_no")
)
def handle_cancel_quiz(call: CallbackQuery) -> None:
    telegram_id = call.from_user.id
    state = ACTIVE_SESSIONS.get(telegram_id)
    if not state:
        bot.answer_callback_query(call.id, "Session expired. Send /start again.")
        return

    if call.data == "cancel_quiz_no":
        bot.answer_callback_query(call.id, "Continuing session.")
        send_current_question(call.message.chat.id, telegram_id)
        return

    # cancel_quiz_yes
    for key in ("session_id", "questions", "current_index"):
        state.pop(key, None)
    state["step"] = "choose_subject"
    ACTIVE_SESSIONS[telegram_id] = state

    bot.answer_callback_query(call.id, "Session cancelled.")
    _show_subjects(call.message.chat.id, telegram_id)


@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_unknown_message(message: Message) -> None:
    """Catch-all handler for unknown commands or text. Guides user back to active state."""
    if route_commands(message):
        return

    telegram_id = message.from_user.id
    text = (message.text or "").strip()

    # Skip if user is admin - let admin handlers deal with admin users
    try:
        from admin.ui_bot import (
            ADMIN_STATE, _is_admin,
            BTN_LIST_DEPTS, BTN_ADD_DEPT, BTN_LIST_SUBJECTS, BTN_ADD_SUBJECT,
            BTN_ADD_QUESTION, BTN_SET_PREMIUM, BTN_SEND_MAIL,
            NAV_HOME as ADMIN_NAV_HOME, NAV_BACK as ADMIN_NAV_BACK,
        )
        if _is_admin(telegram_id):
            # Skip if admin has active state (in a flow)
            if ADMIN_STATE.get(telegram_id):
                return
            # Skip if text matches admin button
            admin_buttons = {
                BTN_LIST_DEPTS, BTN_ADD_DEPT, BTN_LIST_SUBJECTS, BTN_ADD_SUBJECT,
                BTN_ADD_QUESTION, BTN_SET_PREMIUM, BTN_SEND_MAIL,
                ADMIN_NAV_HOME, ADMIN_NAV_BACK,
            }
            if text in admin_buttons:
                return
    except ImportError:
        pass

    state = ACTIVE_SESSIONS.get(telegram_id, {})
    step = state.get("step")

    if not state.get("db_user_id"):
        bot.reply_to(
            message,
            "Unknown command. Please send /start to begin.",
        )
        return

    if not state.get("channel_verified"):
        _show_join_required(message.chat.id, telegram_id)
        return

    if step == "in_quiz":
        bot.reply_to(
            message,
            "You are in a quiz session. Use Home or Back buttons, or answer the question.",
            reply_markup=_quiz_nav_keyboard(),
        )
        return

    if step == "choose_quiz_type":
        kb = _quiz_type_keyboard()
        msg = bot.reply_to(
            message,
            "Unknown input. Please choose a practice mode:",
            reply_markup=kb,
        )
        bot.register_next_step_handler(msg, handle_quiz_type_select)
        return

    if step == "choose_subject":
        department_id = state.get("department_id")
        if department_id:
            kb = _subjects_keyboard(department_id)
            if kb:
                msg = bot.reply_to(
                    message,
                    "Unknown input. Please choose a subject:",
                    reply_markup=kb,
                )
                bot.register_next_step_handler(msg, handle_subject_select_text)
                return

    # Default: go back to department selection
    kb = _departments_keyboard()
    msg = bot.reply_to(
        message,
        "Unknown input. Please choose your department:",
        reply_markup=kb,
    )
    bot.register_next_step_handler(msg, handle_department_select_text)
