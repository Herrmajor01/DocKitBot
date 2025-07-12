"""
Обработчик Telegram бота для DocKitBot
"""

import os
from typing import Any, Dict, List

from loguru import logger
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import Config
from document_processor import DocumentProcessor
from file_handler import FileHandler


class BotHandler:
    def __init__(self):
        self.config = Config()
        self.document_processor = DocumentProcessor()
        self.file_handler = FileHandler()

        # Словарь для хранения состояния пользователей
        self.user_sessions: Dict[int, Dict[str, Any]] = {}

    def _get_user_session(self, user_id: int) -> Dict[str, Any]:
        """Получает или создает сессию пользователя"""
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {
                'files': [],
                'processing': False,
                'last_message_id': None
            }
            logger.info(f"Создана новая сессия для пользователя {user_id}")
        else:
            files_count = len(self.user_sessions[user_id]['files'])
            logger.info(
                f"Получена существующая сессия для пользователя {user_id}, "
                f"файлов: {files_count}")
        return self.user_sessions[user_id]

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "Пользователь"

        welcome_message = f"""
🤖 Добро пожаловать в DocKitBot, {username}!

Я помогу вам автоматически обработать комплект юридических документов:

📋 **Что я умею:**
• Принимать документы (PDF, JPG, PNG) и архивы ZIP
• Автоматически распаковывать ZIP архивы
• Автоматически выравнивать ориентацию документов
• Конвертировать изображения в PDF
• Объединять многостраничные документы
• Создавать итоговый архив с описью

📤 **Как использовать:**
1. Отправьте мне файлы (по одному или несколько)
2. Используйте /process для начала обработки
3. Получите готовый архив и опись!

💡 **Советы:**
• Называйте файлы осмысленно (например: "Договор №1 от 01.01.2025 г.")
• Для многостраничных документов используйте: "стр. 1", "стр. 2" и т.д.
• Максимальный размер файла: 50MB

Используйте /help для получения справки.
        """

        await update.message.reply_text(
            welcome_message,
            parse_mode=ParseMode.MARKDOWN
        )

        logger.info(f"Пользователь {user_id} запустил бота")

    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_message = """
📚 **Справка по использованию DocKitBot**

🔄 **Процесс обработки:**
1. Отправьте документы (по одному или несколько)
2. Используйте /process для начала обработки
3. Получите готовый архив и опись

📁 **Поддерживаемые форматы:**
• Изображения: JPG, JPEG, PNG
• Документы: PDF
• Архивы: ZIP

📝 **Правила именования файлов:**
• Используйте осмысленные названия
• Примеры:
  - "Заявка №11 от 11.11.2024 г..jpg"
  - "Транспортная накладная №1 от 01.01.2025 г. стр. 1.png"
  - "Почтовая квитанция трек №423423422.jpeg"

📄 **Многостраничные документы:**
Добавляйте к названию:
• "стр. 1", "стр. 2" (русский)
• "с. 1", "с. 2" (сокращенно)
• "page 1", "page 2" (английский)

⚠️ **Ограничения:**
• Максимальный размер файла: 50MB
• Общий размер архива: 100MB
• Время обработки: до 30 секунд на файл

🆘 **Если что-то пошло не так:**
Бот сообщит об ошибках и предложит решения.
        """

        await update.message.reply_text(
            help_message,
            parse_mode=ParseMode.MARKDOWN
        )

    async def handle_process(
            self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /process - начало обработки документов"""
        user_id = update.effective_user.id

        # Логируем состояние сессий перед получением
        logger.info(f"Всего сессий в памяти: {len(self.user_sessions)}")
        if user_id in self.user_sessions:
            files_count = len(self.user_sessions[user_id]['files'])
            logger.info(
                f"Сессия пользователя {user_id} существует, "
                f"файлов: {files_count}")
        else:
            logger.info(f"Сессия пользователя {user_id} НЕ существует")

        session = self._get_user_session(user_id)

        files_count = len(session['files'])
        logger.info(
            f"Команда /process от пользователя {user_id}, "
            f"файлов в сессии: {files_count}")

        if not session['files']:
            await update.message.reply_text(
                "❌ Нет документов для обработки. Сначала отправьте файлы!"
            )
            return

        # Создаем клавиатуру для подтверждения
        keyboard = [
            [
                InlineKeyboardButton("✅ Да, обработать",
                                     callback_data="process_yes"),
                InlineKeyboardButton("❌ Отмена", callback_data="process_no")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Показываем список файлов для обработки
        def escape_markdown(text):
            return text.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]')

        files_list = "\n".join(
            [f"• {escape_markdown(os.path.basename(f))}" for f in session['files']])
        message_text = f"""
📋 **Готов к обработке {len(session['files'])} документов:**

{files_list}

Нажмите "✅ Да, обработать" для начала обработки.
        """

        logger.info(
            f"Отправляю сообщение с кнопками для пользователя {user_id}")
        try:
            await update.message.reply_text(
                message_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            logger.info(
                f"Сообщение с кнопками отправлено для пользователя {user_id}")
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения с кнопками: {e}")
            # Попробуем отправить без Markdown
            try:
                await update.message.reply_text(
                    f"📋 Готов к обработке {len(session['files'])} документов:\n\n{files_list}\n\nНажмите кнопку для обработки.",
                    reply_markup=reply_markup
                )
                logger.info(
                    f"Сообщение без Markdown отправлено для пользователя {user_id}")
            except Exception as e2:
                logger.error(f"Ошибка отправки сообщения без Markdown: {e2}")
                await update.message.reply_text("❌ Ошибка отображения списка файлов. Попробуйте еще раз.",
                                                )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback кнопок"""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        session = self._get_user_session(user_id)

        if query.data == "process_yes":
            session['processing'] = True
            await self._process_user_files(update, context, user_id)
        elif query.data == "process_no":
            session['files'] = []
            session['processing'] = False
            await query.edit_message_text("❌ Обработка отменена.")

    async def _process_user_files(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Обрабатывает все файлы пользователя"""
        session = self._get_user_session(user_id)

        if not session['files']:
            return

        # Отправляем сообщение о начале обработки
        progress_message = await update.callback_query.edit_message_text(
            "🔄 Начинаю обработку документов...\n\n"
            "⏳ Прогресс: 0%"
        )

        try:
            # Обрабатываем файлы с показом прогресса
            result = await self._process_files_with_progress(
                session['files'], user_id, progress_message
            )

            if result['success']:
                # Отправляем результат
                await self._send_processing_result(update, result, user_id)
            else:
                await progress_message.edit_text(
                    f"❌ Ошибка обработки: {result['error']}"
                )

        except Exception as e:
            logger.error(
                f"Ошибка обработки файлов пользователя {user_id}: {e}")
            await progress_message.edit_text(
                "❌ Произошла ошибка при обработке. Попробуйте еще раз."
            )
        finally:
            # Очищаем сессию
            session['files'] = []
            session['processing'] = False

    async def _process_files_with_progress(self, files: List[str], user_id: int, progress_message) -> Dict[str, Any]:
        """Обрабатывает файлы с показом прогресса"""
        total_files = len(files)
        processed_files = []
        errors = []

        for i, file_path in enumerate(files, 1):
            try:
                # Обновляем прогресс
                progress = int((i - 1) / total_files * 100)
                progress_bar = self._create_progress_bar(progress)

                await progress_message.edit_text(
                    f"🔄 Обработка документов...\n\n"
                    f"📄 Файл {i} из {total_files}: {os.path.basename(file_path)}\n"
                    f"⏳ Прогресс: {progress}%\n"
                    f"{progress_bar}"
                )

                # Обрабатываем файл
                file_info = self.file_handler.get_file_info(file_path)
                processed_file = await self.document_processor._process_file(file_path, file_info)

                if processed_file:
                    processed_files.append(processed_file)
                else:
                    errors.append(
                        f"Не удалось обработать: {os.path.basename(file_path)}")

            except Exception as e:
                logger.error(f"Ошибка обработки файла {file_path}: {e}")
                errors.append(
                    f"Ошибка обработки {os.path.basename(file_path)}: {str(e)}")

        if not processed_files:
            return {'success': False, 'error': 'Не удалось обработать ни одного файла'}

        # Группируем и объединяем многостраничные документы
        final_files = await self.document_processor._group_and_merge_pages(processed_files)

        # Создаем архив
        archive_path = self.file_handler.create_archive(final_files, user_id)

        # Формируем опись
        inventory = self.document_processor._create_inventory(final_files)

        # Очищаем временные файлы
        self.file_handler.cleanup_user_files(user_id)

        return {
            'success': True,
            'archive_path': archive_path,
            'inventory': inventory,
            'errors': errors
        }

    def _create_progress_bar(self, percentage: int) -> str:
        """Создает текстовый прогресс-бар"""
        bar_length = 20
        filled_length = int(bar_length * percentage / 100)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        return f"[{bar}] {percentage}%"

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик загруженных документов"""
        user_id = update.effective_user.id
        session = self._get_user_session(user_id)
        document = update.message.document

        # Проверяем размер файла
        if document.file_size > self.config.MAX_FILE_SIZE:
            await update.message.reply_text(
                f"❌ Файл слишком большой! Максимальный размер: 50MB\n"
                f"Размер вашего файла: {document.file_size / 1024 / 1024:.1f}MB"
            )
            return

        # Проверяем формат файла
        file_name = document.file_name.lower()
        file_ext = os.path.splitext(file_name)[1]

        # Проверяем поддерживаемые форматы (документы + архивы)
        supported_formats = self.config.SUPPORTED_DOCUMENT_FORMATS + \
            self.config.SUPPORTED_ARCHIVE_FORMATS

        if file_ext not in supported_formats:
            await update.message.reply_text(
                f"❌ Неподдерживаемый формат файла: {file_ext}\n"
                f"Поддерживаемые форматы: {', '.join(supported_formats)}"
            )
            return

        try:
            # Скачиваем файл
            file_path = await self.file_handler.download_file(document, user_id)

            # Если это ZIP архив, распаковываем его
            if file_ext == '.zip':
                extracted_files = self.file_handler.extract_archive(
                    file_path, user_id)
                if extracted_files:
                    session['files'].extend(extracted_files)
                    files_count = len(extracted_files)
                    logger.info(
                        f"ZIP архив распакован: {files_count} файлов "
                        f"добавлено в сессию пользователя {user_id}")
                else:
                    await update.message.reply_text(
                        "⚠️ ZIP архив не содержит поддерживаемых файлов.\n"
                        f"Поддерживаемые форматы: {', '.join(self.config.SUPPORTED_DOCUMENT_FORMATS)}"
                    )
                    return
            else:
                # Добавляем обычный файл в сессию пользователя
                session['files'].append(file_path)

            # Определяем сообщение в зависимости от типа файла
            if file_ext == '.zip':
                total_files = len(session['files'])
                logger.info(
                    f"ZIP архив добавлен в сессию пользователя {user_id}: "
                    f"{document.file_name}, всего файлов: {total_files}")
                status_message = (
                    f"✅ ZIP архив распакован: {document.file_name}\n"
                    f"📁 Всего файлов: {total_files}\n\n"
                    f"Отправьте еще файлы или используйте /process для обработки."
                )
            else:
                total_files = len(session['files'])
                logger.info(
                    f"Файл добавлен в сессию пользователя {user_id}: "
                    f"{document.file_name}, всего файлов: {total_files}")
                status_message = (
                    f"✅ Файл добавлен: {document.file_name}\n"
                    f"📁 Всего файлов: {total_files}\n\n"
                    f"Отправьте еще файлы или используйте /process для обработки."
                )

            # Всегда отправляем уведомление пользователю
            logger.info(
                f"Подготовка к отправке статусного сообщения "
                f"для пользователя {user_id}")
            try:
                # Всегда отправляем новое сообщение для архивов
                if file_ext == '.zip':
                    logger.info(
                        f"Отправляем новое сообщение для ZIP архива "
                        f"пользователя {user_id}")
                    message = await update.message.reply_text(status_message)
                    session['last_message_id'] = message.message_id
                    logger.info(
                        f"Новое сообщение для ZIP архива отправлено "
                        f"пользователю {user_id}")
                # Для обычных файлов используем обновление сообщения
                elif (len(session['files']) == 1 or
                      not session.get('last_message_id')):
                    logger.info(
                        f"Отправляем новое сообщение для пользователя {user_id}")
                    message = await update.message.reply_text(status_message)
                    session['last_message_id'] = message.message_id
                    logger.info(
                        f"Новое сообщение отправлено для пользователя {user_id}")
                else:
                    # Пытаемся обновить предыдущее сообщение
                    msg_id = session['last_message_id']
                    logger.info(
                        f"Пытаемся обновить сообщение {msg_id} "
                        f"для пользователя {user_id}")
                    try:
                        await context.bot.edit_message_text(
                            status_message,
                            chat_id=user_id,
                            message_id=msg_id
                        )
                        logger.info(
                            f"Сообщение обновлено для пользователя {user_id}")
                    except Exception as e:
                        # Если не удалось отредактировать, отправляем новое
                        logger.warning(
                            f"Не удалось отредактировать сообщение: {e}")
                        message = await update.message.reply_text(status_message)
                        session['last_message_id'] = message.message_id
                        logger.info(
                            f"Новое сообщение отправлено после ошибки "
                            f"редактирования для пользователя {user_id}")
            except Exception as e:
                logger.error(f"Ошибка отправки статусного сообщения: {e}")
                # В крайнем случае отправляем простое уведомление
                try:
                    await update.message.reply_text("✅ Файлы добавлены в сессию")
                    logger.info(
                        f"Резервное сообщение отправлено для пользователя {user_id}")
                except Exception as e2:
                    logger.error(
                        f"Не удалось отправить даже резервное сообщение: {e2}")

        except Exception as e:
            logger.error(f"Ошибка обработки документа: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при обработке документа. Попробуйте еще раз."
            )

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик загруженных фотографий"""
        user_id = update.effective_user.id
        session = self._get_user_session(user_id)
        photo = update.message.photo[-1]  # Берем самое качественное фото

        # Проверяем размер файла
        if photo.file_size > self.config.MAX_FILE_SIZE:
            await update.message.reply_text(
                f"❌ Фото слишком большое! Максимальный размер: 50MB\n"
                f"Размер вашего фото: {photo.file_size / 1024 / 1024:.1f}MB"
            )
            return

        try:
            # Скачиваем файл
            file_path = await self.file_handler.download_photo(photo, user_id)

            # Добавляем в сессию пользователя
            session['files'].append(file_path)

            # Всегда отправляем уведомление пользователю
            photo_status_message = (
                f"✅ Фото добавлено\n"
                f"📁 Всего файлов: {len(session['files'])}\n\n"
                f"Отправьте еще файлы или используйте /process для обработки."
            )

            try:
                # Если это первый файл в сессии, просто отправляем сообщение
                if (len(session['files']) == 1 or
                    not session.get('last_message_id')):
                    message = await update.message.reply_text(photo_status_message)
                    session['last_message_id'] = message.message_id
                else:
                    # Пытаемся обновить предыдущее сообщение
                    try:
                        await context.bot.edit_message_text(
                            photo_status_message,
                            chat_id=user_id,
                            message_id=session['last_message_id']
                        )
                    except Exception as e:
                        # Если не удалось отредактировать, отправляем новое
                        logger.warning(
                            f"Не удалось отредактировать сообщение: {e}")
                        message = await update.message.reply_text(photo_status_message)
                        session['last_message_id'] = message.message_id
            except Exception as e:
                logger.error(f"Ошибка отправки статусного сообщения: {e}")
                # В крайнем случае отправляем простое уведомление
                await update.message.reply_text("✅ Фото добавлено в сессию")

        except Exception as e:
            logger.error(f"Ошибка обработки фото: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при обработке фотографии. Попробуйте еще раз."
            )

    async def _send_processing_result(self, update: Update, result: Dict[str, Any], user_id: int):
        """Отправка результата обработки пользователю"""
        try:
            # Отправляем опись
            if result.get('inventory'):
                # Экранируем специальные символы для Markdown
                inventory_text = result['inventory'].replace('_', '\\_').replace(
                    '*', '\\*').replace('[', '\\[').replace(']', '\\]')
                await update.callback_query.edit_message_text(
                    f"📋 **Опись документов:**\n\n{inventory_text}",
                    parse_mode=ParseMode.MARKDOWN
                )

            # Отправляем архив
            if result.get('archive_path'):
                with open(result['archive_path'], 'rb') as archive:
                    await update.callback_query.message.reply_document(
                        document=archive,
                        filename=f"обработанные_документы_{user_id}.zip",
                        caption="✅ Обработка завершена! Вот ваш архив с документами."
                    )

            # Отправляем отчет об ошибках
            if result.get('errors'):
                error_report = "⚠️ **Отчет об ошибках:**\n\n"
                for error in result['errors']:
                    # Экранируем специальные символы
                    safe_error = error.replace('_', '\\_').replace(
                        '*', '\\*').replace('[', '\\[').replace(']', '\\]')
                    error_report += f"• {safe_error}\n"
                await update.callback_query.message.reply_text(
                    error_report,
                    parse_mode=ParseMode.MARKDOWN
                )

        except Exception as e:
            logger.error(f"Ошибка отправки результата: {e}")
            await update.callback_query.message.reply_text(
                "❌ Ошибка при отправке результата. Попробуйте еще раз."
            )
