#!/usr/bin/env python3
"""
DocKitBot - Telegram бот для обработки юридических документов
"""

import os

from dotenv import load_dotenv
from loguru import logger
from telegram import Update
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          MessageHandler, filters)

from bot_handler import BotHandler
from config import Config

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logger.add("logs/bot.log", rotation="1 day", retention="7 days", level="INFO")


class DocKitBot:
    def __init__(self):
        self.config = Config()
        self.bot_handler = BotHandler()

    async def start_command(self, update: Update, context):
        """Обработчик команды /start"""
        await self.bot_handler.handle_start(update, context)

    async def help_command(self, update: Update, context):
        """Обработчик команды /help"""
        await self.bot_handler.handle_help(update, context)

    async def handle_document(self, update: Update, context):
        """Обработчик загруженных документов"""
        await self.bot_handler.handle_document(update, context)

    async def handle_photo(self, update: Update, context):
        """Обработчик загруженных фотографий"""
        await self.bot_handler.handle_photo(update, context)

    async def handle_process(self, update: Update, context):
        """Обработчик команды /process"""
        await self.bot_handler.handle_process(update, context)

    async def handle_callback(self, update: Update, context):
        """Обработчик callback кнопок"""
        await self.bot_handler.handle_callback(update, context)

    def run(self):
        """Запуск бота"""
        # Создаем папки для логов и временных файлов
        os.makedirs("logs", exist_ok=True)
        os.makedirs("temp", exist_ok=True)
        os.makedirs("output", exist_ok=True)

        # Инициализируем приложение
        application = Application.builder().token(self.config.TELEGRAM_TOKEN).build()

        # Добавляем обработчики
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("process", self.handle_process))
        application.add_handler(MessageHandler(
            filters.Document.ALL, self.handle_document))
        application.add_handler(MessageHandler(
            filters.PHOTO, self.handle_photo))
        application.add_handler(CallbackQueryHandler(self.handle_callback))

        logger.info("Бот запущен")

        # Запускаем бота
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    bot = DocKitBot()
    bot.run()
