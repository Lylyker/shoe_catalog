"""Инициализация складского учёта: статусы, склады, перенос текущих остатков.

    python manage.py init_stock
Идемпотентно — повторный запуск не дублирует данные и не ломает остатки.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import ProductVariant
from supply.models import StatusSupply, StockBalance, Warehouse

STATUSES = [('Черновик', 'draft'), ('Проведена', 'posted'), ('Отменена', 'cancelled')]
WAREHOUSES = [
    ('Основной склад', 'г. Москва, ул. Складская, д. 1', True),
    ('Розничный зал', 'г. Москва, ТЦ «Обувной», павильон 12', False),
]


class Command(BaseCommand):
    help = 'Создаёт статусы поставок, склады и переносит остатки в складской учёт'

    @transaction.atomic
    def handle(self, *args, **options):
        for name, code in STATUSES:
            StatusSupply.objects.get_or_create(code=code, defaults={'name': name})

        for name, address, is_default in WAREHOUSES:
            Warehouse.objects.get_or_create(
                name=name, defaults={'address': address, 'is_default': is_default})

        main = Warehouse.objects.filter(is_default=True).first() or Warehouse.objects.first()
        moved = 0
        for variant in ProductVariant.objects.all():
            if StockBalance.objects.filter(product_variant=variant).exists():
                continue
            StockBalance.objects.create(warehouse=main, product_variant=variant,
                                        quantity=variant.quantity)
            moved += 1

        self.stdout.write(self.style.SUCCESS(
            f'Готово. Складов: {Warehouse.objects.count()}, '
            f'статусов: {StatusSupply.objects.count()}, '
            f'перенесено остатков: {moved}.'))