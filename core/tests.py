"""Регрессионные тесты: суррогаты не должны попадать в БД и имена файлов."""
import tempfile

from django.core.files.base import ContentFile
from django.test import TestCase
from django.utils import timezone

from catalog.models import Brand, Category, Product, Season, Style, TargetGroup
from shoe_catalog.storage import SafeFileSystemStorage

from .sanitize import has_surrogates, strip_surrogates


def make_surrogate(text):
    """Имитирует имя файла, декодированное из UTF-8 в ASCII+surrogateescape."""
    return text.encode('utf-8').decode('ascii', 'surrogateescape')


class SanitizeTests(TestCase):
    def test_restores_cyrillic(self):
        broken = make_surrogate('кроссовки.png')
        self.assertTrue(has_surrogates(broken))
        self.assertEqual(strip_surrogates(broken), 'кроссовки.png')

    def test_plain_text_untouched(self):
        for value in ('Air Max 90', 'Кроссовки Nike', '', None, 42):
            self.assertEqual(strip_surrogates(value), value)


class StorageTests(TestCase):
    def test_save_with_surrogate_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = SafeFileSystemStorage(location=tmp)
            name = storage.save(make_surrogate('фото_товара.png'), ContentFile(b'data'))
            self.assertFalse(has_surrogates(name))
            self.assertTrue(storage.exists(name))


class ModelSaveTests(TestCase):
    def setUp(self):
        self.defaults = dict(
            category=Category.objects.create(name='Кроссовки'),
            brand=Brand.objects.create(name='Nike'),
            season=Season.objects.create(name='Лето'),
            style=Style.objects.create(name='Спорт'),
            target_group=TargetGroup.objects.create(name='Мужчины'),
            date_receipt=timezone.now().date(),
        )

    def test_presave_strips_surrogates(self):
        product = Product.objects.create(
            name=make_surrogate('Air Max 90'),
            description=make_surrogate('Описание товара'),
            retail_price='3500.00',
            **self.defaults,
        )
        product.refresh_from_db()
        self.assertEqual(product.name, 'Air Max 90')
        self.assertEqual(product.description, 'Описание товара')
        self.assertFalse(has_surrogates(product.name))