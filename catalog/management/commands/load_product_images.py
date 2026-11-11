"""
Загрузка фотографий товаров: python manage.py load_product_images

11 товаров получают реальные фото обуви, один товар (Summer Sandal Wave)
намеренно остаётся без изображения — для демонстрации плейсхолдера image-off.
Если какой-то URL недоступен, генерируется локальная PNG-заглушка,
поэтому ни одна карточка не ломается.
Повторный запуск не перекачивает уже загруженные фото (ключ --force обновляет).
"""
import io
import urllib.request

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from PIL import Image, ImageDraw

from catalog.models import Product

# name товара -> стабильный ID фото на CDN Unsplash
IMAGES = {
    'Air Max 90': 'photo-1542291026-7eec264c27ff',
    'Run': 'photo-1605348532760-6753d2c43329',
    'Ultraboost 22': 'photo-1606107557195-0e29a4b5b4aa',
    'Suede Classic': 'photo-1525966222134-fcfa99b8ae77',
    '574 Core': 'photo-1552346154-21d32810aba3',
    'Chuck Taylor All Star': 'photo-1595341888016-a392ef81b7de',
    'Old Skool': 'photo-1549298916-b41d501d3772',
    '1460 Smooth': 'photo-1520639888713-7851133b1ed0',
    '6-Inch Premium': 'photo-1542840410-3092f99611a3',
    'Oxford Classic': 'photo-1614252369475-531eba835eb1',
    'Winter Boot Alaska': 'photo-1605733513597-a8f8341084e6',
}
WITHOUT_IMAGE = 'Summer Sandal Wave'


def download(url):
    """Скачивает и проверяет, что это действительно изображение."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
        Image.open(io.BytesIO(data)).verify()
        return data
    except Exception:
        return None


def fallback_png(name):
    """Локальная PNG-заглушка в палитре проекта, если CDN недоступен."""
    palette = [(26, 26, 46), (233, 69, 96), (16, 185, 129),
               (37, 99, 235), (245, 158, 11), (139, 92, 246)]
    color = palette[sum(ord(c) for c in name) % len(palette)]
    img = Image.new('RGB', (900, 700), color)
    draw = ImageDraw.Draw(img)
    draw.ellipse((150, 430, 760, 570), fill=(255, 255, 255))
    draw.rectangle((210, 300, 640, 480), fill=(255, 255, 255))
    draw.text((60, 60), name, fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


class Command(BaseCommand):
    help = 'Загружает фото товаров (11 с фото, 1 без фото)'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Перезагрузить фото даже если уже есть')

    def handle(self, *args, **options):
        force = options['force']
        loaded = fallbacks = skipped = 0

        for name, photo_id in IMAGES.items():
            product = Product.objects.filter(name=name).first()
            if not product:
                self.stdout.write(self.style.WARNING(f'Товар не найден: {name}'))
                continue
            if product.photo and not force:
                skipped += 1
                continue

            url = f'https://images.unsplash.com/{photo_id}?auto=format&fit=crop&w=900&q=80'
            data = download(url)
            if data is None:
                data = fallback_png(name)
                ext = 'png'
                fallbacks += 1
            else:
                ext = 'jpg'
                loaded += 1

            if product.photo:
                product.photo.delete(save=False)
            product.photo.save(f'{slugify(name)}.{ext}', ContentFile(data), save=True)
            self.stdout.write(f'Фото установлено: {name}')

        # Гарантированно оставляем одну карточку без изображения
        product = Product.objects.filter(name=WITHOUT_IMAGE).first()
        if product and product.photo:
            product.photo.delete(save=True)

        self.stdout.write(self.style.SUCCESS(
            f'Готово. Загружено фото: {loaded}, локальных заглушек: {fallbacks}, '
            f'пропущено (уже есть): {skipped}. Без изображения: {WITHOUT_IMAGE}'
        ))