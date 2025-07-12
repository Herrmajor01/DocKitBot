"""
Конвертер PDF для DocKitBot
"""

import os
import re
from typing import List, Optional

from loguru import logger
from PIL import Image
from PyPDF2 import PdfReader, PdfWriter

from config import Config


class PDFConverter:
    def __init__(self):
        self.config = Config()

    async def image_to_pdf(self, image_path: str, original_name: str) -> Optional[str]:
        """Конвертирует изображение в PDF"""
        try:
            # Открываем изображение
            with Image.open(image_path) as img:
                # Конвертируем в RGB если нужно
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # Генерируем имя для PDF
                pdf_name = self._get_pdf_name(original_name)
                pdf_path = os.path.join(os.path.dirname(image_path), pdf_name)

                # Сохраняем как PDF
                img.save(pdf_path, 'PDF', resolution=300.0)

                logger.info(f"Изображение конвертировано в PDF: {pdf_path}")
                return pdf_path

        except Exception as e:
            logger.error(
                f"Ошибка конвертации изображения в PDF {image_path}: {e}")
            return None

    async def merge_pdfs(self, pdf_paths: List[str], base_name: str) -> Optional[str]:
        """Объединяет несколько PDF в один"""
        try:
            if not pdf_paths:
                return None

            # Создаем PDF writer
            pdf_writer = PdfWriter()

            # Добавляем страницы из каждого PDF
            for pdf_path in pdf_paths:
                try:
                    with open(pdf_path, 'rb') as pdf_file:
                        pdf_reader = PdfReader(pdf_file)

                        # Добавляем все страницы
                        for page in pdf_reader.pages:
                            pdf_writer.add_page(page)

                except Exception as e:
                    logger.error(f"Ошибка чтения PDF {pdf_path}: {e}")
                    continue

            # Если нет страниц, возвращаем None
            if len(pdf_writer.pages) == 0:
                return None

            # Сохраняем объединенный PDF
            merged_pdf_path = self._get_merged_pdf_path(
                pdf_paths[0], base_name)

            with open(merged_pdf_path, 'wb') as output_file:
                pdf_writer.write(output_file)

            logger.info(f"PDF файлы объединены: {merged_pdf_path}")
            return merged_pdf_path

        except Exception as e:
            logger.error(f"Ошибка объединения PDF: {e}")
            return None

    def _get_pdf_name(self, original_name: str) -> str:
        """Генерирует имя для PDF файла"""
        # Убираем расширение
        name_without_ext = os.path.splitext(original_name)[0]

        # Сохраняем информацию о странице
        page_info = None
        for pattern in self.config.PAGE_PATTERNS:
            match = re.search(pattern, name_without_ext, re.IGNORECASE)
            if match:
                page_info = match.group()
                break

        # Убираем маркеры страниц для базового имени
        for pattern in self.config.PAGE_PATTERNS:
            name_without_ext = re.sub(
                pattern, '', name_without_ext, flags=re.IGNORECASE)

        # Очищаем от лишних пробелов
        clean_name = name_without_ext.strip()

        # Добавляем информацию о странице обратно, если она была
        if page_info:
            clean_name = f"{clean_name} {page_info}"

        # Добавляем расширение PDF
        return f"{clean_name}.pdf"

    def _get_merged_pdf_path(self, first_pdf_path: str, base_name: str) -> str:
        """Генерирует путь для объединенного PDF"""
        directory = os.path.dirname(first_pdf_path)

        # Очищаем базовое имя от недопустимых символов
        clean_base_name = re.sub(r'[<>:"/\\|?*]', '_', base_name)

        merged_filename = f"{clean_base_name}.pdf"
        return os.path.join(directory, merged_filename)

    async def validate_pdf(self, pdf_path: str) -> bool:
        """Проверяет валидность PDF файла"""
        try:
            with open(pdf_path, 'rb') as pdf_file:
                pdf_reader = PdfReader(pdf_file)

                # Проверяем количество страниц
                if len(pdf_reader.pages) == 0:
                    return False

                # Проверяем размер файла
                file_size = os.path.getsize(pdf_path)
                if file_size < 100:  # Минимальный размер PDF
                    return False

                return True

        except Exception as e:
            logger.error(f"Ошибка валидации PDF {pdf_path}: {e}")
            return False

    async def get_pdf_info(self, pdf_path: str) -> dict:
        """Получает информацию о PDF файле"""
        try:
            with open(pdf_path, 'rb') as pdf_file:
                pdf_reader = PdfReader(pdf_file)

                return {
                    'pages': len(pdf_reader.pages),
                    'size': os.path.getsize(pdf_path),
                    'encrypted': pdf_reader.is_encrypted
                }

        except Exception as e:
            logger.error(f"Ошибка получения информации о PDF {pdf_path}: {e}")
            return {}

    async def optimize_pdf(self, pdf_path: str) -> str:
        """Оптимизирует PDF файл"""
        try:
            with open(pdf_path, 'rb') as input_file:
                pdf_reader = PdfReader(input_file)
                pdf_writer = PdfWriter()

                # Добавляем страницы
                for page in pdf_reader.pages:
                    pdf_writer.add_page(page)

                # Генерируем путь для оптимизированного файла
                optimized_path = self._get_optimized_pdf_path(pdf_path)

                # Сохраняем с оптимизацией
                with open(optimized_path, 'wb') as output_file:
                    pdf_writer.write(output_file)

                logger.info(f"PDF оптимизирован: {optimized_path}")
                return optimized_path

        except Exception as e:
            logger.error(f"Ошибка оптимизации PDF {pdf_path}: {e}")
            return pdf_path

    def _get_optimized_pdf_path(self, original_path: str) -> str:
        """Генерирует путь для оптимизированного PDF"""
        directory = os.path.dirname(original_path)
        filename = os.path.basename(original_path)
        name, ext = os.path.splitext(filename)

        optimized_filename = f"{name}_optimized{ext}"
        return os.path.join(directory, optimized_filename)
