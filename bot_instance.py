"""Shared TeleBot instance for user and admin handlers."""

import telebot

from config.settings import bot_settings

bot = telebot.TeleBot(bot_settings.token, parse_mode="HTML")
