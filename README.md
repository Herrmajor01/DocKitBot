# 🤖 DocKitBot

**Telegram bot for processing legal documents with OCR and PDF conversion**

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://core.telegram.org/bots)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 📋 Описание

DocKitBot - это интеллектуальный Telegram бот для обработки юридических документов. Бот автоматически извлекает текст из изображений и PDF файлов, создает описи документов и формирует архивы для удобного хранения.

### ✨ Основные возможности

- 📄 **Обработка документов**: Поддержка PDF, JPG, JPEG, PNG
- 📦 **ZIP архивы**: Автоматическое извлечение и обработка файлов из архивов
- 🔍 **OCR технология**: Извлечение текста из изображений на русском и английском языках
- 📝 **Автоматические описи**: Создание структурированных описей документов
- 🎯 **Определение страниц**: Автоматическое определение номеров страниц
- 🔧 **Исправление кодировок**: Автоматическое исправление проблем с кодировкой имен файлов
- 📱 **Удобный интерфейс**: Простое управление через Telegram

## 🚀 Быстрый старт

### Предварительные требования

- Python 3.9+
- Telegram Bot Token
- Tesseract OCR

### Установка

1. **Клонируйте репозиторий:**
```bash
git clone https://github.com/your-username/DocKitBot.git
cd DocKitBot
```

2. **Создайте виртуальное окружение:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows
```

3. **Установите зависимости:**
```bash
pip install -r requirements.txt
```

4. **Установите Tesseract OCR:**
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-rus

# macOS
brew install tesseract tesseract-lang

# Windows
# Скачайте с https://github.com/UB-Mannheim/tesseract/wiki
```

5. **Настройте переменные окружения:**
```bash
cp env_example.txt .env
# Отредактируйте .env файл, добавив ваш TELEGRAM_TOKEN
```

6. **Запустите бота:**
```bash
python main.py
```

## 📖 Использование

### Команды бота

- `/start` - Начало работы с ботом
- `/help` - Справка по использованию
- `/process` - Начать обработку загруженных документов

### Как использовать

1. **Отправьте документы** боту (PDF, изображения или ZIP архив)
2. **Используйте команду** `/process` для начала обработки
3. **Получите результат** - опись документов и архив с обработанными файлами

### Примеры использования

```
👤 Пользователь: /start
🤖 Бот: Добро пожаловать в DocKitBot!
     Отправьте документы для обработки.

👤 Пользователь: [отправляет PDF файл]
🤖 Бот: ✅ Файл добавлен: договор.pdf
     📁 Всего файлов: 1

     Отправьте еще файлы или используйте /process для обработки.

👤 Пользователь: /process
🤖 Бот: 🔄 Обработка документов...
     [прогресс-бар]
     ✅ Обработка завершена!
```

## 🛠 Технические детали

### Архитектура

- **`main.py`** - Точка входа и настройка бота
- **`bot_handler.py`** - Обработчики команд и сообщений
- **`file_handler.py`** - Работа с файлами и архивами
- **`document_processor.py`** - Обработка документов и создание описей
- **`image_processor.py`** - OCR и обработка изображений
- **`pdf_converter.py`** - Конвертация PDF в изображения
- **`config.py`** - Конфигурация приложения

### Поддерживаемые форматы

- **Документы**: PDF, JPG, JPEG, PNG
- **Архивы**: ZIP (с автоматическим извлечением)
- **Максимальный размер**: 50MB на файл, 100MB на архив

### Особенности

- **Автоматическое исправление кодировок** имен файлов
- **Улучшенное определение ориентации** документов
- **Многоязычный OCR** (русский + английский)
- **Обработка вложенных папок** в ZIP архивах
- **Автоматическая очистка** временных файлов

## 🔧 Настройка

### Переменные окружения

```bash
TELEGRAM_TOKEN=your_bot_token_here
```

### Конфигурация

Основные настройки находятся в `config.py`:

```python
# Ограничения файлов
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_TOTAL_SIZE = 100 * 1024 * 1024  # 100MB

# Поддерживаемые форматы
SUPPORTED_IMAGE_FORMATS = ['.jpg', '.jpeg', '.png']
SUPPORTED_DOCUMENT_FORMATS = ['.pdf'] + SUPPORTED_IMAGE_FORMATS
SUPPORTED_ARCHIVE_FORMATS = ['.zip']

# Настройки OCR
OCR_LANGUAGE = 'rus+eng'  # Русский + английский
OCR_TIMEOUT = 30  # секунды на обработку одного файла
```

## 🐛 Устранение неполадок

### Частые проблемы

1. **Ошибка Tesseract не найден**
   - Убедитесь, что Tesseract установлен и доступен в PATH
   - Проверьте установку языковых пакетов

2. **Проблемы с кодировкой имен файлов**
   - Бот автоматически исправляет большинство проблем
   - Проверьте логи для деталей

3. **Ошибки обработки PDF**
   - Убедитесь, что PDF не защищен паролем
   - Проверьте, что PDF содержит текст или изображения

### Логи

Логи сохраняются в папке `logs/` с подробной информацией о работе бота.

## 🤝 Вклад в проект

Мы приветствуем вклад в развитие проекта!

1. Форкните репозиторий
2. Создайте ветку для новой функции (`git checkout -b feature/amazing-feature`)
3. Зафиксируйте изменения (`git commit -m 'Add amazing feature'`)
4. Отправьте в ветку (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. См. файл `LICENSE` для подробностей.

## 🙏 Благодарности

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot API
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) - OCR движок
- [Pillow](https://python-pillow.org/) - Обработка изображений
- [PyPDF2](https://pypdf2.readthedocs.io/) - Работа с PDF

## 📞 Поддержка

Если у вас есть вопросы или проблемы:

- Создайте [Issue](https://github.com/Herrmajor01/DocKitBot/issues)
- Обратитесь к [документации](https://github.com/Herrmajor01/DocKitBot/wiki)
- @HerrrMajor Telegra

---

⭐ **Если проект вам понравился, поставьте звездочку!**
