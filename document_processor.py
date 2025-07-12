"""
Основной процессор документов для DocKitBot
"""

import os
import re
from collections import defaultdict
from typing import Any, Dict, List, Tuple

from loguru import logger

from config import Config
from file_handler import FileHandler
from image_processor import ImageProcessor
from pdf_converter import PDFConverter


class DocumentProcessor:
    def __init__(self):
        self.config = Config()
        self.image_processor = ImageProcessor()
        self.pdf_converter = PDFConverter()
        self.file_handler = FileHandler()

    async def process_single_file(self, file_path: str, user_id: int) -> Dict[str, Any]:
        """Обрабатывает один файл"""
        try:
            # Получаем информацию о файле
            file_info = self.file_handler.get_file_info(file_path)
            if not file_info:
                return {'success': False, 'error': 'Не удалось получить информацию о файле'}

            # Проверяем имя файла
            validation = self.file_handler.validate_file_name(
                file_info['name'])
            if not validation['valid']:
                return {
                    'success': False,
                    'error': f"Некорректное имя файла: {'; '.join(validation['warnings'])}"
                }

            # Обрабатываем файл
            processed_file = await self._process_file(file_path, file_info)

            if not processed_file:
                return {'success': False, 'error': 'Не удалось обработать файл'}

            # Создаем архив с одним файлом
            archive_path = self.file_handler.create_archive(
                [processed_file], user_id)

            # Формируем опись
            inventory = self._create_inventory([processed_file])

            # Очищаем временные файлы
            self.file_handler.cleanup_user_files(user_id)

            return {
                'success': True,
                'archive_path': archive_path,
                'inventory': inventory,
                'errors': validation.get('warnings', [])
            }

        except Exception as e:
            logger.error(f"Ошибка обработки файла {file_path}: {e}")
            return {'success': False, 'error': str(e)}

    async def process_multiple_files(self, file_paths: List[str], user_id: int) -> Dict[str, Any]:
        """Обрабатывает несколько файлов"""
        try:
            processed_files = []
            errors = []

            # Обрабатываем каждый файл
            for file_path in file_paths:
                try:
                    file_info = self.file_handler.get_file_info(file_path)
                    if not file_info:
                        errors.append(
                            f"Не удалось получить информацию о файле: {file_path}")
                        continue

                    # Проверяем имя файла
                    validation = self.file_handler.validate_file_name(
                        file_info['name'])
                    if validation['warnings']:
                        errors.extend(validation['warnings'])

                    # Обрабатываем файл
                    processed_file = await self._process_file(file_path, file_info)
                    if processed_file:
                        processed_files.append(processed_file)
                    else:
                        errors.append(
                            f"Не удалось обработать файл: {file_info['name']}")

                except Exception as e:
                    logger.error(f"Ошибка обработки файла {file_path}: {e}")
                    errors.append(
                        f"Ошибка обработки {os.path.basename(file_path)}: {str(e)}")

            if not processed_files:
                return {'success': False, 'error': 'Не удалось обработать ни одного файла'}

            # Группируем и объединяем многостраничные документы
            final_files = await self._group_and_merge_pages(processed_files)

            # Создаем архив
            archive_path = self.file_handler.create_archive(
                final_files, user_id)

            # Формируем опись
            inventory = self._create_inventory(final_files)

            # Очищаем временные файлы
            self.file_handler.cleanup_user_files(user_id)

            return {
                'success': True,
                'archive_path': archive_path,
                'inventory': inventory,
                'errors': errors
            }

        except Exception as e:
            logger.error(f"Ошибка обработки множественных файлов: {e}")
            return {'success': False, 'error': str(e)}

    async def _process_file(self, file_path: str, file_info: Dict[str, Any]) -> str:
        """Обрабатывает один файл (поворот, конвертация)"""
        try:
            file_ext = file_info['extension']

            # Если это PDF, просто копируем
            if file_ext == '.pdf':
                return file_path

            # Если это изображение, обрабатываем
            if file_ext in self.config.SUPPORTED_IMAGE_FORMATS:
                # Определяем и исправляем ориентацию
                corrected_image = await self.image_processor.correct_orientation(file_path)

                # Конвертируем в PDF
                pdf_path = await self.pdf_converter.image_to_pdf(corrected_image, file_info['name'])

                # Удаляем временное изображение
                if corrected_image != file_path:
                    os.remove(corrected_image)

                return pdf_path

            return None

        except Exception as e:
            logger.error(f"Ошибка обработки файла {file_path}: {e}")
            return None

    async def _group_and_merge_pages(self, processed_files: List[str]) -> List[str]:
        """Группирует и объединяет многостраничные документы"""
        try:
            logger.info(f"Начинаю группировку {len(processed_files)} файлов")

            # Группируем файлы по базовому имени
            file_groups = defaultdict(list)

            for file_path in processed_files:
                file_name = os.path.basename(file_path)
                base_name, page_info = self._extract_base_name_and_page(
                    file_name)
                logger.info(
                    f"Файл: {file_name} -> базовое имя: '{base_name}', страница: {page_info}")
                file_groups[base_name].append((file_path, page_info))

            logger.info(f"Найдено групп: {len(file_groups)}")
            for base_name, files in file_groups.items():
                logger.info(f"Группа '{base_name}': {len(files)} файлов")

            final_files = []

            for base_name, files_with_pages in file_groups.items():
                if len(files_with_pages) == 1:
                    # Одностраничный документ
                    logger.info(f"Одностраничный документ: {base_name}")
                    final_files.append(files_with_pages[0][0])
                else:
                    # Многостраничный документ
                    logger.info(
                        f"Многостраничный документ: {base_name}, файлов: {len(files_with_pages)}")
                    # Сортируем по номеру страницы
                    sorted_files = sorted(
                        files_with_pages, key=lambda x: x[1] if x[1] else 0)

                    logger.info(f"Отсортированные файлы для {base_name}:")
                    for file_path, page_num in sorted_files:
                        logger.info(
                            f"  Страница {page_num}: {os.path.basename(file_path)}")

                    # Объединяем в один PDF
                    file_paths = [f[0] for f in sorted_files]
                    merged_pdf = await self.pdf_converter.merge_pdfs(file_paths, base_name)

                    if merged_pdf:
                        logger.info(f"PDF объединен: {merged_pdf}")
                        final_files.append(merged_pdf)
                    else:
                        # Если не удалось объединить, добавляем по отдельности
                        logger.warning(
                            f"Не удалось объединить PDF для {base_name}")
                        final_files.extend(file_paths)

            logger.info(f"Итоговое количество файлов: {len(final_files)}")
            return final_files

        except Exception as e:
            logger.error(f"Ошибка группировки файлов: {e}")
            return processed_files

    def _extract_base_name_and_page(self, file_name: str) -> Tuple[str, int]:
        """Извлекает базовое имя и номер страницы из имени файла"""
        # Убираем расширение
        name_without_ext = os.path.splitext(file_name)[0]
        logger.info(f"Анализирую имя файла: '{name_without_ext}'")

        # Ищем паттерны страниц
        for pattern in self.config.PAGE_PATTERNS:
            match = re.search(pattern, name_without_ext, re.IGNORECASE)
            if match:
                # Извлекаем номер страницы
                page_text = match.group()
                page_number = re.search(r'\d+', page_text)
                if page_number:
                    page_num = int(page_number.group())
                    # Убираем информацию о странице из имени
                    base_name = re.sub(
                        pattern, '', name_without_ext, flags=re.IGNORECASE).strip()
                    logger.info(
                        f"Найден паттерн '{pattern}': страница {page_num}, базовое имя: '{base_name}'")
                    return base_name, page_num

        # Если страница не найдена
        logger.info(f"Страница не найдена, базовое имя: '{name_without_ext}'")
        return name_without_ext, None

    def _create_inventory(self, files: List[str]) -> str:
        """Создает опись документов"""
        inventory = "📋 **Опись документов:**\n\n"

        for i, file_path in enumerate(files, 1):
            file_name = os.path.basename(file_path)
            # Убираем расширение для отображения
            display_name = os.path.splitext(file_name)[0]
            inventory += f"{i}. {display_name}.pdf\n"

        return inventory
