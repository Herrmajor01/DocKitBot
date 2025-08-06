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
            r'ст\.?\s*\d+',     # ст.1, ст 1
            r'стр\.?\s*\d+',    # стр.1, стр 1
            r'стр\s*\d+',       # стр1
            r'с\.?\s*\d+',      # с.1, с 1
            r'страница\s*\d+',  # страница 1
            r'page\s*\d+',      # page 1
            r'p\.?\s*\d+'       # p.1, p 1
        ]

        # Настройки OCR
        # Русский + английский
        self.OCR_LANGUAGE = 'rus+eng'
        # секунды на обработку одного файла (увеличено для больших файлов)
        self.OCR_TIMEOUT = 120

        # Пути к папкам
        self.TEMP_DIR = "temp"
        self.OUTPUT_DIR = "output"
        self.LOGS_DIR = "logs"

        # Настройки обработки
        # Максимум файлов для одновременной обработки
        self.MAX_CONCURRENT_FILES = 5
        # Время хранения временных файлов (1 час)
        self.CLEANUP_DELAY = 3600
