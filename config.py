"""
Конфигурация для DocKitBot
"""

import os


class Config:
    def __init__(self):
        # Telegram Bot Token
        self.TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
        if not self.TELEGRAM_TOKEN:
            raise ValueError(
                "TELEGRAM_TOKEN не установлен в переменных окружения")

        # Ограничения файлов
        # 50MB - максимальный размер файла в Telegram
        self.MAX_FILE_SIZE = 50 * 1024 * 1024
        # 100MB - общий лимит для архива
        self.MAX_TOTAL_SIZE = 100 * 1024 * 1024

        # Поддерживаемые форматы
        self.SUPPORTED_IMAGE_FORMATS = ['.jpg', '.jpeg', '.png']
        self.SUPPORTED_DOCUMENT_FORMATS = [
            '.pdf'] + self.SUPPORTED_IMAGE_FORMATS
        self.SUPPORTED_ARCHIVE_FORMATS = ['.zip']

        # Паттерны для определения страниц
        self.PAGE_PATTERNS = [
            r'стр\.?\s*\d+',
            r'стр\s*\d+',  # Добавляем паттерн без точки
            r'с\.?\s*\d+',
            r'страница\s*\d+',
            r'page\s*\d+',
            r'p\.?\s*\d+'
        ]

        # Настройки OCR
        # Русский + английский
        self.OCR_LANGUAGE = 'rus+eng'
        # секунды на обработку одного файла
        self.OCR_TIMEOUT = 30

        # Пути к папкам
        self.TEMP_DIR = "temp"
        self.OUTPUT_DIR = "output"
        self.LOGS_DIR = "logs"

        # Настройки обработки
        # Максимум файлов для одновременной обработки
        self.MAX_CONCURRENT_FILES = 5
        # Время хранения временных файлов (1 час)
        self.CLEANUP_DELAY = 3600
