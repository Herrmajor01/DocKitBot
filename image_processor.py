"""
Обработчик изображений для DocKitBot
"""

import asyncio
import os
import re
from typing import Optional

import pytesseract
from loguru import logger
from PIL import Image

from config import Config


class ImageProcessor:
    def __init__(self):
        self.config = Config()

    async def correct_orientation(self, image_path: str) -> str:
        """Определяет и исправляет ориентацию изображения"""
        try:
            # Открываем изображение
            with Image.open(image_path) as img:
                # Проверяем EXIF данные для ориентации
                exif_orientation = self._get_exif_orientation(img)

                # Если EXIF показывает правильную ориентацию (1), доверяем ему
                if exif_orientation == 1:
                    logger.info(
                        f"EXIF показывает правильную ориентацию для {image_path}")
                    return image_path

                # Определяем текущую ориентацию с помощью OCR
                current_orientation = await self._detect_orientation(img)

                # Если ориентация правильная, возвращаем исходный файл
                if current_orientation == 0:
                    logger.info(
                        f"OCR подтвердил правильную ориентацию для {image_path}")
                    return image_path

                # Поворачиваем изображение
                rotated_img = img.rotate(-current_orientation, expand=True)

                # Сохраняем исправленное изображение
                corrected_path = self._get_corrected_path(image_path)
                rotated_img.save(corrected_path, quality=95, optimize=True)

                logger.info(
                    f"Ориентация исправлена: {image_path} -> {corrected_path}"
                    f", поворот: {current_orientation}°")
                return corrected_path

        except Exception as e:
            logger.error(f"Ошибка исправления ориентации {image_path}: {e}")
            return image_path

    async def _detect_orientation(self, img: Image.Image) -> int:
        """Определяет ориентацию изображения с помощью OCR"""
        try:
            # Конвертируем в RGB если нужно
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Получаем размеры изображения
            width, height = img.size

            # Если изображение слишком маленькое, пропускаем OCR
            if width < 100 or height < 100:
                logger.warning("Изображение слишком маленькое для OCR")
                return 0

            # Пробуем определить ориентацию с помощью Tesseract
            try:
                # Настройки OCR для лучшего определения ориентации
                # Пробуем разные языки для определения ориентации
                try:
                    custom_config = r'--oem 3 --psm 0 -l rus+eng'
                    osd = await asyncio.wait_for(
                        asyncio.to_thread(
                            pytesseract.image_to_osd, img,
                            config=custom_config),
                        timeout=self.config.OCR_TIMEOUT
                    )
                except Exception:
                    try:
                        custom_config = r'--oem 3 --psm 0 -l eng'
                        osd = await asyncio.wait_for(
                            asyncio.to_thread(
                                pytesseract.image_to_osd, img,
                                config=custom_config),
                            timeout=self.config.OCR_TIMEOUT
                        )
                    except Exception:
                        # Если языковые модели не работают, пробуем без них
                        custom_config = r'--oem 3 --psm 0'
                        osd = await asyncio.wait_for(
                            asyncio.to_thread(
                                pytesseract.image_to_osd, img,
                                config=custom_config),
                            timeout=self.config.OCR_TIMEOUT
                        )

                # Извлекаем угол поворота
                rotate_match = re.search(r'Rotate: (\d+)', osd)
                if rotate_match:
                    angle = int(rotate_match.group(1))
                    logger.info(
                        f"OCR определил угол поворота: {angle} градусов")
                    return angle
                else:
                    logger.warning("OCR не смог определить угол поворота")
                    return 0

            except Exception as ocr_error:
                logger.warning(
                    f"OCR не смог определить ориентацию: {ocr_error}")

                # Пробуем эвристический метод
                return await self._heuristic_orientation_detection(img)

        except Exception as e:
            logger.error(f"Ошибка определения ориентации: {e}")
            return 0

    async def _heuristic_orientation_detection(self, img: Image.Image) -> int:
        """Эвристический метод определения ориентации"""
        try:
            width, height = img.size

            # Если изображение квадратное, не поворачиваем
            if abs(width - height) < min(width, height) * 0.1:
                return 0

            # Пробуем OCR на повернутых версиях изображения
            angles_to_try = [90, 180, 270]
            best_angle = 0
            best_confidence = 0

            for angle in angles_to_try:
                try:
                    rotated = img.rotate(angle, expand=True)

                    # Пробуем распознать текст с таймаутом
                    text = await asyncio.wait_for(
                        asyncio.to_thread(
                            pytesseract.image_to_string,
                            rotated,
                            lang='rus',
                            config='--oem 3 --psm 6'
                        ),
                        timeout=30  # Короткий таймаут для эвристики
                    )

                    # Простая оценка качества распознавания
                    # Считаем количество букв и цифр
                    confidence = len([c for c in text if c.isalnum()])

                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_angle = angle

                except Exception:
                    continue

            # Если нашли достаточно текста, возвращаем лучший угол
            if best_confidence > 10:
                logger.info(
                    f"Эвристический метод определил угол: {best_angle}")
                return best_angle

            return 0

        except Exception as e:
            logger.error(f"Ошибка эвристического определения ориентации: {e}")
            return 0

    def _get_exif_orientation(self, img: Image.Image) -> Optional[int]:
        """Получает ориентацию из EXIF данных"""
        try:
            if hasattr(img, '_getexif') and img._getexif() is not None:
                exif = img._getexif()
                if exif is not None:
                    # EXIF tag для ориентации
                    orientation_tag = 274
                    return exif.get(orientation_tag, 1)
        except Exception as e:
            logger.debug(f"Ошибка получения EXIF ориентации: {e}")
        return None

    def _get_corrected_path(self, original_path: str) -> str:
        """Генерирует путь для исправленного изображения"""
        directory = os.path.dirname(original_path)
        filename = os.path.basename(original_path)
        name, ext = os.path.splitext(filename)

        corrected_filename = f"{name}_corrected{ext}"
        return os.path.join(directory, corrected_filename)

    async def validate_image(self, image_path: str) -> bool:
        """Проверяет валидность изображения"""
        try:
            with Image.open(image_path) as img:
                # Проверяем формат
                if img.format not in ['JPEG', 'PNG']:
                    return False

                # Проверяем размеры
                width, height = img.size
                if width < 50 or height < 50:
                    return False

                # Проверяем, что изображение не пустое
                if img.getbbox() is None:
                    return False

                return True

        except Exception as e:
            logger.error(f"Ошибка валидации изображения {image_path}: {e}")
            return False

    async def optimize_image(self, image_path: str) -> str:
        """Оптимизирует изображение для лучшего OCR"""
        try:
            with Image.open(image_path) as img:
                # Конвертируем в RGB
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # Увеличиваем контрастность для лучшего OCR
                from PIL import ImageEnhance
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.5)  # Увеличиваем контрастность на 50%

                # Сохраняем оптимизированное изображение
                optimized_path = self._get_optimized_path(image_path)
                img.save(optimized_path, quality=95, optimize=True)

                return optimized_path

        except Exception as e:
            logger.error(f"Ошибка оптимизации изображения {image_path}: {e}")
            return image_path

    def _get_optimized_path(self, original_path: str) -> str:
        """Генерирует путь для оптимизированного изображения"""
        directory = os.path.dirname(original_path)
        filename = os.path.basename(original_path)
        name, ext = os.path.splitext(filename)

        optimized_filename = f"{name}_optimized{ext}"
        return os.path.join(directory, optimized_filename)
