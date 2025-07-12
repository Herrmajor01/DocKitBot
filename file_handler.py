"""
Обработчик файлов для DocKitBot
"""

import os
import shutil
import zipfile
from typing import Any, Dict, List

from loguru import logger
from telegram import Document, PhotoSize

from config import Config


class FileHandler:
    def __init__(self):
        self.config = Config()

    async def download_file(self, document: Document, user_id: int) -> str:
        """Скачивает файл из Telegram и возвращает путь к нему"""
        try:
            # Создаем папку для пользователя
            user_temp_dir = os.path.join(self.config.TEMP_DIR, str(user_id))
            os.makedirs(user_temp_dir, exist_ok=True)

            # Восстанавливаем оригинальное имя файла и исправляем кодировку
            original_name = self._restore_file_name(document.file_name)
            # Дополнительно пытаемся исправить кодировку
            original_name = self._fix_filename_encoding(original_name)

            # Скачиваем файл
            file_path = os.path.join(user_temp_dir, original_name)
            file = await document.get_file()
            await file.download_to_drive(file_path)

            logger.info(f"Файл скачан: {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"Ошибка скачивания файла: {e}")
            raise

    async def download_photo(self, photo: PhotoSize, user_id: int) -> str:
        """Скачивает фото из Telegram и возвращает путь к нему"""
        try:
            # Создаем папку для пользователя
            user_temp_dir = os.path.join(self.config.TEMP_DIR, str(user_id))
            os.makedirs(user_temp_dir, exist_ok=True)

            # Генерируем имя файла
            file_name = f"photo_{user_id}_{photo.file_id}.jpg"
            file_path = os.path.join(user_temp_dir, file_name)

            # Скачиваем фото
            file = await photo.get_file()
            await file.download_to_drive(file_path)

            logger.info(f"Фото скачано: {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"Ошибка скачивания фото: {e}")
            raise

    def extract_archive(self, archive_path: str, user_id: int) -> List[str]:
        """Распаковывает архив и возвращает список путей к файлам"""
        try:
            extract_dir = os.path.join(
                self.config.TEMP_DIR, str(user_id), "extracted")
            os.makedirs(extract_dir, exist_ok=True)
            extracted_files = []
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                for file_name in file_list:
                    if (file_name.endswith('/') or
                        file_name.startswith('__MACOSX/')):
                        continue
                    file_ext = os.path.splitext(file_name)[1].lower()
                    if file_ext not in self.config.SUPPORTED_DOCUMENT_FORMATS:
                        logger.warning(
                            f"Неподдерживаемый формат в архиве: "
                            f"{file_name}")
                        continue
                    # Извлекаем файл
                    zip_ref.extract(file_name, extract_dir)
                    extracted_path = os.path.join(extract_dir, file_name)

                    # Исправляем кодировку и нормализуем имя
                    fixed_name = self._fix_filename_encoding(file_name)
                    fixed_name = self._restore_file_name(fixed_name)

                    if fixed_name != file_name:
                        # Создаем новый путь с исправленным именем
                        fixed_path = os.path.join(extract_dir, fixed_name)

                        # Создаем директории для нового пути, если нужно
                        fixed_dir = os.path.dirname(fixed_path)
                        if fixed_dir and not os.path.exists(fixed_dir):
                            os.makedirs(fixed_dir, exist_ok=True)

                        # Переименовываем файл, если новый путь не существует
                        if not os.path.exists(fixed_path):
                            try:
                                os.rename(extracted_path, fixed_path)
                                extracted_path = fixed_path
                            except OSError as e:
                                logger.warning(
                                    f"Не удалось переименовать файл "
                                    f"{extracted_path} -> {fixed_path}: {e}")
                                # Если переименование не удалось, используем исходный путь
                                pass

                    extracted_files.append(extracted_path)
            logger.info(f"Архив распакован: {len(extracted_files)} файлов")
            return extracted_files
        except zipfile.BadZipFile:
            raise ValueError("Поврежденный или неподдерживаемый архив")
        except Exception as e:
            logger.error(f"Ошибка распаковки архива: {e}")
            raise

    def create_archive(self, files: List[str], user_id: int) -> str:
        """Создает архив из обработанных файлов"""
        try:
            # Создаем папку для выходных файлов
            output_dir = os.path.join(self.config.OUTPUT_DIR, str(user_id))
            os.makedirs(output_dir, exist_ok=True)

            # Путь к итоговому архиву
            archive_path = os.path.join(
                output_dir, f"processed_documents_{user_id}.zip")

            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
                for file_path in files:
                    if os.path.exists(file_path):
                        # Добавляем файл в архив с очищенным именем
                        file_name = os.path.basename(file_path)
                        # Очищаем имя файла от лишних символов
                        clean_name = self._clean_final_filename(file_name)
                        # Используем UTF-8 кодировку для имен файлов в архиве
                        zip_ref.write(file_path, clean_name.encode(
                            'utf-8').decode('utf-8'))

            logger.info(f"Архив создан: {archive_path}")
            return archive_path

        except Exception as e:
            logger.error(f"Ошибка создания архива: {e}")
            raise

    def cleanup_user_files(self, user_id: int):
        """Очищает временные файлы пользователя"""
        try:
            user_temp_dir = os.path.join(self.config.TEMP_DIR, str(user_id))
            if os.path.exists(user_temp_dir):
                shutil.rmtree(user_temp_dir)
                logger.info(f"Временные файлы пользователя {user_id} очищены")
        except Exception as e:
            logger.error(f"Ошибка очистки файлов пользователя {user_id}: {e}")

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Получает информацию о файле"""
        try:
            stat = os.stat(file_path)
            return {
                'name': os.path.basename(file_path),
                'size': stat.st_size,
                'extension': os.path.splitext(file_path)[1].lower(),
                'path': file_path
            }
        except Exception as e:
            logger.error(
                f"Ошибка получения информации о файле {file_path}: {e}")
            return {}

    def _fix_filename_encoding(self, file_name: str) -> str:
        """Исправляет кодировку имени файла из ZIP архива или Telegram"""
        try:
            # Сначала пробуем системное исправление кодировки
            if self._contains_mojibake(file_name):
                # Пробуем разные кодировки для исправления
                fixed_name = self._try_decode_with_encodings(file_name)
                if fixed_name != file_name:
                    logger.info(
                        f"Исправлено кодировкой: {file_name} -> {fixed_name}")
                    return fixed_name

            # Если системное исправление не помогло, используем словарь замен
            return self._apply_replacement_fixes(file_name)

        except Exception as e:
            logger.warning(
                f"Ошибка исправления кодировки файла {file_name}: {e}")
            return file_name

    def _contains_mojibake(self, text: str) -> bool:
        """Проверяет, содержит ли текст кракозябры"""
        # Проверяем наличие типичных символов кракозябр
        mojibake_chars = [
            '╨', '╤', '╠', '╡', '╛', '╜', '╝',
            '╞', '╟', '╢', '╣', '╚', '╔', '╦', '╩', '╬',
            '╨₧', '╤é', '╤ç', '╨╡', '╤â', '╨┐', '╨╛', '╨▓',
            '╨░', '╨╜', '╨╕', '╨╗', '╨╢', '╨▒', '╨┤', '╨╝',
            '╨╣', '╨║', '╨│', '╨╖', '╨╪', '╨Ю', '╨Я', '╨Ъ',
            '╨Ы', '╨Ь', '╨Э', '╨Ч', '╨Ш', '╨Щ', 'Γäû'
        ]
        return any(char in text for char in mojibake_chars)

    def _try_decode_with_encodings(self, text: str) -> str:
        """Пробует исправить кодировку разными способами"""
        # Сначала пробуем прямое декодирование из разных кодировок
        direct_encodings = [
            'cp866',      # Русская DOS
            'windows-1251',  # Русская Windows
            'cp1252',     # Западноевропейская
            'iso-8859-1',  # Latin-1
            'cp437',      # OEM US
            'cp850',      # OEM Multilingual
        ]

        for encoding in direct_encodings:
            try:
                # Пробуем декодировать напрямую
                decoded = text.encode('latin1').decode(encoding)
                # Проверяем, что получилась читаемая строка с кириллицей
                if any('А' <= ch <= 'я' or ch == 'ё' for ch in decoded):
                    return decoded
            except Exception:
                continue

        # Пробуем двойное декодирование для сложных случаев
        double_encodings = [
            ('utf-8', 'cp1252'),
            ('utf-8', 'iso-8859-1'),
            ('windows-1251', 'cp1252'),
            ('cp866', 'cp1252'),
        ]

        for first_enc, second_enc in double_encodings:
            try:
                # Двойное декодирование
                step1 = text.encode(second_enc).decode(first_enc)
                if any('А' <= ch <= 'я' or ch == 'ё' for ch in step1):
                    return step1
            except Exception:
                continue

        return text

    def _apply_replacement_fixes(self, file_name: str) -> str:
        """Применяет словарь замен для исправления кракозябр"""
        # Специальные замены для часто встречающихся проблем
        replacements = {
            '╨í╨ó╨í': 'СТС',
            '╨ó╤Ç╨░╨╜╤ü╨┐╨╛╤Ç╤é╨╜╨░╤Å': 'Транспортная',
            '╨╜╨░╨║╨╗╨░╨┤╨╜╨░╤Å': 'накладная',
            '╨ö╨╛╨│╨╛╨▓╨╛╤Ç': 'Договор',
            '╨╛╨║╨░╨╖╨░╨╜╨╕╤Å': 'оказания',
            '╤Ä╤Ç╨╕╨┤╨╕╤ç╨╡╤ü╨║╨╕╤à': 'юридических',
            '╤â╤ü╨╗╤â╨│': 'услуг',
            '╨Æ╨╛╨┤╨╕╤é╨╡╨╗╤î╤ü╨╛╨╡': 'Водительское',
            '╤â╨┤╨╛╤ü╤é╨╛╨▓╨╡╤Ç╨╡╨╜╨╕╨╡': 'удостоверение',
            '╨ƒ╨╗╨░╤é╨╡╨╢╨╜╨╛╨╡': 'Платежное',
            '╨┐╨╛╤Ç╤â╤ç╨╡╨╜╨╕╨╡': 'поручение',
            '╨ù╨░╤Å╨▓╨║╨░': 'Заявка',
            '╤ü╤é╤Ç': 'стр',
            '╤ü': 'с',
            '╨│': 'г',
            '╨╛╤é': 'от',
            'Γäû': '№',
            # Добавляем новые замены для конкретных кракозябр
            '╨ó╤Ç╤â╨┤╨╛╨▓╨╛╨╕╠å': 'Трудовой',
            '╨┤╨╛г╨╛╨▓╨╛╤Ç': 'договор',
            '╨Æ╨╛╨┤╨╕╤é╨╡╨╗╤î': 'Водитель',
            '╤ü╨║╨╛╨╡': 'ское',
            '╨Æ╨╛╨┤╨╕╤é╨╡╨╗╤îс╨║╨╛╨╡': 'Водительское',
            'Водительс╨║╨╛╨╡': 'Водительское',
            '╨║╨╛╨╡': 'кое',
            # Новые замены для конкретной кракозябры
            '╨₧╤é╤ç╨╡╤é': 'Отчет',
            '╨₧╤é╨▓╨╡╤é': 'Ответ',
            '╨₧╤é╨▓╨╡╤é╤ç': 'Ответ',
            '╨╛╨▒': 'об',
            'отс╨╗╨╡╨╢╨╕╨▓╨░╨╜╨╕╨╕': 'отслеживании',
            '╨┐╨╛╤ç╤é╨╛╨▓╨╛г╨╛': 'почтового',
            'от╨┐╤Ç╨░╨▓╨╗╨╡╨╜╨╕╤Å': 'отправления',
            '╨ó╤Ç╨░╨╜с╨┐╤Çот╨╜╨░╤Å': 'Транспортная',
            # Дополнительные замены для улучшения качества
            '╨╛╨▒ отс╨╗╨╡╨╢╨╕╨▓╨░╨╜╨╕╨╕': 'об отслеживании',
            '╨┐╨╛╤ç╤é╨╛╨▓╨╛г╨╛ от╨┐╤Ç╨░╨▓╨╗╨╡╨╜╨╕╤Å': 'почтового отправления',
            # Замены для отдельных символов
            '╨₧': 'О',
            '╤é': 'т',
            '╤ç': 'ч',
            '╨╡': 'е',
            '╤â': 'у',
            '╨┐': 'п',
            '╨╛': 'о',
            '╨▓': 'в',
            '╨░': 'а',
            '╨╜': 'н',
            '╨╕': 'и',
            '╨╗': 'л',
            '╨╢': 'ж',
            '╨▒': 'б',
            '╨┤': 'д',
            '╨╝': 'м',
            '╨╣': 'й',
            '╨║': 'к',
            '╨│': 'г',
            '╨╖': 'з',
            '╨╪': 'М',
            '╨Ю': 'Ю',
            '╨Я': 'Я',
            '╨Ъ': 'Ъ',
            '╨Ы': 'Ы',
            '╨Ь': 'Ь',
            '╨Э': 'Э',
            '╨Ч': 'Ч',
            '╨Ш': 'Ш',
            '╨Щ': 'Щ',
            # Дополнительные замены для конкретных кракозябр из логов
            '╨¥': 'Н',
            '╤Å': 'я',
        }

        fixed_name=file_name
        for wrong, correct in replacements.items():
            fixed_name=fixed_name.replace(wrong, correct)

        # Если были замены, логируем
        if fixed_name != file_name:
            logger.info(f"Исправлено заменами: {file_name} -> {fixed_name}")

        return fixed_name

    def _restore_file_name(self, file_name: str) -> str:
        """Восстанавливает оригинальное имя файла, заменяя подчеркивания на пробелы"""
        # Заменяем подчеркивания на пробелы, но сохраняем расширение
        name, ext=os.path.splitext(file_name)
        restored_name=name.replace('_', ' ')

        # Восстанавливаем даты (заменяем пробелы на точки в датах)
        import re

        # Паттерн для дат вида "DD MM YYYY" или "DD MM YYYY г"
        date_pattern=r'(\d{1,2})\s+(\d{1,2})\s+(\d{4})(\s+г)?'

        def replace_date(match):
            day, month, year, g=match.groups()
            result=f"{day}.{month}.{year}"
            if g:
                result += " г."
            return result

        restored_name=re.sub(date_pattern, replace_date, restored_name)

        # Восстанавливаем некоторые специальные символы
        restored_name=restored_name.replace('№', '№')  # Номер
        restored_name=restored_name.replace(
            ' от ', ' от ')  # Нормализуем пробелы вокруг "от"

        # Убираем лишние пробелы и символы в конце
        restored_name=' '.join(restored_name.split())

        # Убираем лишние символы в конце имени (точки, пробелы, подчеркивания)
        restored_name=restored_name.rstrip(' ._-')

        return restored_name + ext

    def _clean_final_filename(self, file_name: str) -> str:
        """Очищает финальное имя файла от лишних символов"""
        # Убираем расширение
        name, ext=os.path.splitext(file_name)

        # Убираем лишние символы в конце имени
        clean_name=name.rstrip(' ._-')

        # Убираем лишние пробелы
        clean_name=' '.join(clean_name.split())

        return clean_name + ext

    def validate_file_name(self, file_name: str) -> Dict[str, Any]:
        """Проверяет корректность имени файла"""
        result={
            'valid': True,
            'warnings': [],
            'suggestions': []
        }

        # Проверяем длину имени
        if len(file_name) > 200:
            result['valid']=False
            result['warnings'].append("Имя файла слишком длинное")

        # Проверяем наличие расширения
        if '.' not in file_name:
            result['warnings'].append("Файл без расширения")

        # Проверяем специальные символы
        invalid_chars=['<', '>', ':', '"', '|', '?', '*']
        for char in invalid_chars:
            if char in file_name:
                result['warnings'].append(
                    f"Содержит недопустимый символ: {char}")

        # Проверяем осмысленность имени
        meaningful_words=['договор', 'заявка',
                            'накладная', 'квитанция', 'счет', 'акт']
        file_lower=file_name.lower()
        has_meaningful=any(word in file_lower for word in meaningful_words)

        if not has_meaningful:
            result['suggestions'].append(
                "Используйте осмысленные названия документов")

        return result
