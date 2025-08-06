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
        """Объединяет несколько PDF в один с правильной ориентацией текста"""
        try:
            if not pdf_paths:
                return None

            # Сначала обрабатываем каждый PDF для правильной ориентации
            corrected_pdfs = []
            for pdf_path in pdf_paths:
                try:
                    # Конвертируем PDF в изображения для анализа ориентации
                    images = await self.pdf_to_images(pdf_path)
                    if not images:
                        logger.warning(f"Не удалось конвертировать PDF в изображения: {pdf_path}")
                        corrected_pdfs.append(pdf_path)
                        continue

                    # Проверяем ориентацию текста каждой страницы
                    corrected_images = []
                    needs_correction = False

                    for i, image_path in enumerate(images):
                        # Импортируем image_processor для определения ориентации
                        from image_processor import ImageProcessor
                        image_processor = ImageProcessor()

                        # Определяем правильную ориентацию текста с помощью OCR
                        corrected_image = await image_processor.correct_orientation(image_path)
                        if corrected_image != image_path:
                            needs_correction = True
                            logger.info(f"Страница {i+1} требует исправления ориентации")
                        corrected_images.append(corrected_image)

                    if needs_correction:
                        # Объединяем исправленные изображения обратно в PDF
                        corrected_pdf = await self.images_to_pdf(
                            corrected_images,
                            f"corrected_{os.path.splitext(os.path.basename(pdf_path))[0]}"
                        )

                        # Очищаем временные изображения
                        for img_path in images + corrected_images:
                            if img_path != pdf_path and os.path.exists(img_path):
                                os.remove(img_path)

                        if corrected_pdf:
                            corrected_pdfs.append(corrected_pdf)
                            logger.info(f"PDF ориентация исправлена: {pdf_path} -> {corrected_pdf}")
                        else:
                            corrected_pdfs.append(pdf_path)
                    else:
                        # Очищаем временные изображения
                        for img_path in images:
                            if img_path != pdf_path and os.path.exists(img_path):
                                os.remove(img_path)
                        corrected_pdfs.append(pdf_path)
                        logger.info(f"PDF ориентация корректна: {pdf_path}")

                except Exception as e:
                    logger.error(f"Ошибка обработки ориентации PDF {pdf_path}: {e}")
                    corrected_pdfs.append(pdf_path)

            # Теперь объединяем исправленные PDF
            pdf_writer = PdfWriter()

            for pdf_path in corrected_pdfs:
                try:
                    with open(pdf_path, 'rb') as pdf_file:
                        pdf_reader = PdfReader(pdf_file)
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

            logger.info(f"PDF файлы объединены с правильной ориентацией: {merged_pdf_path}")
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

    async def pdf_to_images(self, pdf_path: str) -> List[str]:
        """Конвертирует PDF в список изображений"""
        try:
            import fitz  # PyMuPDF

            # Открываем PDF
            doc = fitz.open(pdf_path)
            image_paths = []

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)

                # Рендерим страницу как изображение с высоким разрешением
                mat = fitz.Matrix(2.0, 2.0)  # 2x zoom для лучшего качества
                pix = page.get_pixmap(matrix=mat)

                # Сохраняем изображение
                image_path = os.path.join(
                    os.path.dirname(pdf_path),
                    f"{os.path.splitext(os.path.basename(pdf_path))[0]}_page_{page_num + 1}.png"
                )
                pix.save(image_path)
                image_paths.append(image_path)

            doc.close()
            logger.info(f"PDF конвертирован в {len(image_paths)} изображений: {pdf_path}")
            return image_paths

        except ImportError:
            logger.warning("PyMuPDF не установлен, используем fallback метод")
            return await self._pdf_to_images_fallback(pdf_path)
        except Exception as e:
            logger.error(f"Ошибка конвертации PDF в изображения {pdf_path}: {e}")
            return []

    async def _pdf_to_images_fallback(self, pdf_path: str) -> List[str]:
        """Fallback метод конвертации PDF в изображения без PyMuPDF"""
        try:
            from pdf2image import convert_from_path

            # Конвертируем PDF в изображения
            images = convert_from_path(pdf_path, dpi=300)
            image_paths = []

            for i, image in enumerate(images):
                image_path = os.path.join(
                    os.path.dirname(pdf_path),
                    f"{os.path.splitext(os.path.basename(pdf_path))[0]}_page_{i + 1}.png"
                )
                image.save(image_path, 'PNG')
                image_paths.append(image_path)

            logger.info(f"PDF конвертирован в {len(image_paths)} изображений (fallback): {pdf_path}")
            return image_paths

        except ImportError:
            logger.error("pdf2image не установлен, невозможно конвертировать PDF в изображения")
            return []
        except Exception as e:
            logger.error(f"Ошибка fallback конвертации PDF в изображения {pdf_path}: {e}")
            return []

    async def images_to_pdf(self, image_paths: List[str], base_name: str) -> Optional[str]:
        """Конвертирует список изображений в PDF"""
        try:
            if not image_paths:
                return None

            # Создаем PDF
            pdf_path = os.path.join(
                os.path.dirname(image_paths[0]),
                f"{base_name}.pdf"
            )

            # Открываем первое изображение для определения размера
            with Image.open(image_paths[0]) as first_img:
                # Конвертируем в RGB если нужно
                if first_img.mode != 'RGB':
                    first_img = first_img.convert('RGB')

                # Создаем список изображений
                images = []
                for img_path in image_paths:
                    with Image.open(img_path) as img:
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        images.append(img.copy())

                # Сохраняем как PDF
                first_img.save(pdf_path, 'PDF', save_all=True, append_images=images[1:])

            logger.info(f"Изображения конвертированы в PDF: {pdf_path}")
            return pdf_path

        except Exception as e:
            logger.error(f"Ошибка конвертации изображений в PDF: {e}")
            return None

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
