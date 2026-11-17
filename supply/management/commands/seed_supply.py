"""Демо-данные модуля поставок: поставщики и две поставки (проведённая и черновик).

    python manage.py seed_supply
"""
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import transaction
from django.utils import timezone

from catalog.models import ProductVariant
from supply.models import StatusSupply, Supplier, Supply, SupplyItem, Warehouse
from supply.services import post_supply

SUPPLIERS = [
    ('ООО «СпортСнаб»', 'Смирнов Алексей Петрович', '+74951234567',
     'info@sportsnab.ru', '7701234567', 'г. Москва, ул. Оптовая, д. 5'),
    ('АО «ОбувьОпт»', 'Кузнецова Ольга Ивановна', '+78129876543',
     'sales@obuvopt.ru', '7802345678', 'г. Санкт-Петербург, пр. Складской, д. 18'),
    ('ИП Петров В. А.', 'Петров Владимир Андреевич', '+79031112233',
     'petrov@mail.ru', '770812345678', 'г. Подольск, ул. Промышленная, д. 3'),
]


class Command(BaseCommand):
    help = 'Наполняет модуль поставок демо-данными'

    @transaction.atomic
    def handle(self, *args, **options):
        call_command('init_stock')

        suppliers = []
        for name, person, phone, email, inn, address in SUPPLIERS:
            supplier, _ = Supplier.objects.get_or_create(
                name=name,
                defaults={'contact_person': person, 'phone': phone,
                          'email': email, 'inn': inn, 'address': address})
            suppliers.append(supplier)

        warehouse = Warehouse.objects.filter(is_default=True).first()
        today = timezone.localdate()
        variants = list(ProductVariant.objects.select_related('product').order_by('id')[:6])
        if not variants:
            self.stdout.write(self.style.WARNING('Нет вариантов товаров. Сначала seed_data.'))
            return

        posted = Supply.objects.filter(note='Демо-поставка (проведена)').first()
        if not posted:
            posted = Supply.objects.create(
                supplier=suppliers[0], warehouse=warehouse,
                status=StatusSupply.objects.get(code='draft'),
                date_supply=today - timedelta(days=7),
                note='Демо-поставка (проведена)')
            for variant in variants[:3]:
                SupplyItem.objects.create(
                    supply=posted, product_variant=variant, quantity=10,
                    purchase_price=(variant.product.retail_price * Decimal('0.6')).quantize(Decimal('0.01')))
            post_supply(posted)
            self.stdout.write(f'Проведена поставка {posted.number}')

        draft = Supply.objects.filter(note='Демо-поставка (черновик)').first()
        if not draft:
            draft = Supply.objects.create(
                supplier=suppliers[1], warehouse=warehouse,
                status=StatusSupply.objects.get(code='draft'),
                date_supply=today,
                note='Демо-поставка (черновик)')
            for variant in variants[3:]:
                SupplyItem.objects.create(
                    supply=draft, product_variant=variant, quantity=5,
                    purchase_price=(variant.product.retail_price * Decimal('0.55')).quantize(Decimal('0.01')))
            self.stdout.write(f'Создан черновик {draft.number}')

        self.stdout.write(self.style.SUCCESS(
            f'Готово. Поставщиков: {Supplier.objects.count()}, '
            f'поставок: {Supply.objects.count()}, '
            f'позиций: {SupplyItem.objects.count()}.'))