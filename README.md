# HEEE Preparation Bot

Telegram quiz bot built with `pyTelegramBotAPI` and MySQL.

## Main pieces

- **`config/`**: Environment and database configuration.
- **`db/`**: Low-level DB connector and query helpers.
- **`models/`**: Data access layer for each table.
- **`bot/`**: Telegram bot handlers for users.
- **`admin/`**: Simple CLI admin tools to manage departments, questions, and options.

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the main bot:

```bash
python main.py
```
