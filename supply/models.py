"""Модуль поставок и складского учёта.

Supply — шапка поставки, SupplyItem — её позиции.
StockBalance — остаток варианта товара на конкретном складе.
StockMovement — журнал движений (приход/расход) для аудита и корректных возвратов.
ProductVariant.quantity поддерживается как сумма остатков по всем складам.
"""
from django.db import models
from django.utils import timezone

from catalog.models import ProductVariant
from users.models import User


class StatusSupply(models.Model):
    """Статус поставки: черновик / проведена / отменена."""
    name = models.CharField(max_length=50, unique=True, verbose_name='Название')
    code = models.CharField(max_length=20, unique=True, verbose_name='Код',
                            help_text='draft, posted или cancelled')

    class Meta:
        verbose_name = 'Статус поставки'
        verbose_name_plural = 'Статусы поставок'

    def __str__(self):
        return self.name


class Supplier(models.Model):
    """Поставщик обуви."""
    name = models.CharField(max_length=150, unique=True, verbose_name='Наименование')
    contact_person = models.CharField(max_length=150, blank=True, verbose_name='Контактное лицо')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')
    email = models.EmailField(blank=True, verbose_name='E-mail')
    inn = models.CharField(max_length=12, blank=True, verbose_name='ИНН')
    address = models.TextField(blank=True, verbose_name='Адрес')
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    class Meta:
        verbose_name = 'Поставщик'
        verbose_name_plural = 'Поставщики'
        ordering = ['name']

    def __str__(self):
        return self.name


class Warehouse(models.Model):
    """Склад хранения товаров."""
    name = models.CharField(max_length=150, unique=True, verbose_name='Название')
    address = models.TextField(blank=True, verbose_name='Адрес')
    is_default = models.BooleanField(default=False, verbose_name='Склад по умолчанию')
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    class Meta:
        verbose_name = 'Склад'
        verbose_name_plural = 'Склады'
        ordering = ['-is_default', 'name']

    def __str__(self):
        return self.name

    def get_total_quantity(self):
        return self.balances.aggregate(s=models.Sum('quantity'))['s'] or 0


class Supply(models.Model):
    """Поставка товаров от поставщика на склад."""
    number = models.CharField(max_length=20, unique=True, blank=True, verbose_name='Номер')
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT,
                                 related_name='supplies', verbose_name='Поставщик')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT,
                                  related_name='supplies', verbose_name='Склад')
    status = models.ForeignKey(StatusSupply, on_delete=models.PROTECT,
                               related_name='supplies', verbose_name='Статус')
    date_supply = models.DateField(default=timezone.localdate, verbose_name='Дата поставки')
    note = models.TextField(blank=True, verbose_name='Примечание')

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='supplies_created', verbose_name='Создал')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создана')
    posted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='supplies_posted', verbose_name='Провёл')
    posted_at = models.DateTimeField(null=True, blank=True, verbose_name='Проведена')

    class Meta:
        verbose_name = 'Поставка'
        verbose_name_plural = 'Поставки'
        ordering = ['-date_supply', '-id']

    def __str__(self):
        return f'{self.number or "Черновик"} от {self.date_supply:%d.%m.%Y}'

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating and not self.number:
            self.number = f'POST-{self.pk:05d}'
            super().save(update_fields=['number'])

    @property
    def code(self):
        return self.status.code if self.status_id else ''

    @property
    def is_draft(self):
        return self.code == 'draft'

    @property
    def is_posted(self):
        return self.code == 'posted'

    @property
    def is_cancelled(self):
        return self.code == 'cancelled'

    def get_total_quantity(self):
        return self.items.aggregate(s=models.Sum('quantity'))['s'] or 0

    def get_total_price(self):
        return sum((item.get_subtotal() for item in self.items.all()), 0)


class SupplyItem(models.Model):
    """Позиция поставки: конкретный размерно-цветовой вариант и закупочная цена."""
    supply = models.ForeignKey(Supply, on_delete=models.CASCADE,
                               related_name='items', verbose_name='Поставка')
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT,
                                        related_name='supply_items', verbose_name='Вариант товара')
    quantity = models.PositiveIntegerField(verbose_name='Количество')
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2,
                                         verbose_name='Закупочная цена')

    class Meta:
        verbose_name = 'Позиция поставки'
        verbose_name_plural = 'Позиции поставки'
        unique_together = ('supply', 'product_variant')

    def __str__(self):
        return f'{self.product_variant} × {self.quantity}'

    def get_subtotal(self):
        return self.quantity * self.purchase_price


class StockBalance(models.Model):
    """Остаток варианта товара на складе."""
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE,
                                  related_name='balances', verbose_name='Склад')
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE,
                                        related_name='balances', verbose_name='Вариант товара')
    quantity = models.PositiveIntegerField(default=0, verbose_name='Количество')

    class Meta:
        verbose_name = 'Остаток на складе'
        verbose_name_plural = 'Остатки на складах'
        unique_together = ('warehouse', 'product_variant')
        ordering = ['warehouse', 'product_variant']

    def __str__(self):
        return f'{self.product_variant} @ {self.warehouse}: {self.quantity}'


class StockMovement(models.Model):
    """Журнал движений товара: приход положительный, расход отрицательный."""
    REASON_CHOICES = [
        ('supply', 'Поставка'),
        ('cancel', 'Отмена поставки'),
        ('order', 'Заказ'),
        ('return', 'Возврат по заказу'),
        ('manual', 'Корректировка'),
    ]

    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE,
                                        related_name='movements', verbose_name='Вариант товара')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT,
                                  related_name='movements', verbose_name='Склад')
    quantity = models.IntegerField(verbose_name='Изменение количества')
    reason = models.CharField(max_length=20, choices=REASON_CHOICES, verbose_name='Основание')
    supply = models.ForeignKey(Supply, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='movements', verbose_name='Поставка')
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='movements', verbose_name='Заказ')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='movements', verbose_name='Пользователь')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата операции')

    class Meta:
        verbose_name = 'Движение товара'
        verbose_name_plural = 'Журнал движений'
        ordering = ['-created_at', '-id']

    def __str__(self):
        sign = '+' if self.quantity > 0 else ''
        return f'{sign}{self.quantity} {self.product_variant} ({self.get_reason_display()})'