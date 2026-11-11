from django.db import models
from django.utils import timezone
from catalog.models import ProductVariant
from users.models import User


class StatusBasket(models.Model):
    """Статус корзины (Активна, Оформлена, Отменена)"""
    name = models.CharField(max_length=50, verbose_name="Название статуса")

    class Meta:
        verbose_name = "Статус корзины"
        verbose_name_plural = "Статусы корзин"

    def __str__(self):
        return self.name


class StatusOrder(models.Model):
    """Статус заказа (Новый, В обработке, Отправлен, Выполнен, Отменен)"""
    name = models.CharField(max_length=50, verbose_name="Название статуса")

    class Meta:
        verbose_name = "Статус заказа"
        verbose_name_plural = "Статусы заказов"

    def __str__(self):
        return self.name


class DeliveryMethod(models.Model):
    """Способ доставки (Курьер, Самовывоз, Почта и т.д.)"""
    name = models.CharField(max_length=100, verbose_name="Название способа")
    description = models.TextField(blank=True, verbose_name="Описание")

    class Meta:
        verbose_name = "Способ доставки"
        verbose_name_plural = "Способы доставки"

    def __str__(self):
        return self.name


class Basket(models.Model):
    """Корзина пользователя"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='baskets',
        verbose_name="Пользователь"
    )
    status = models.ForeignKey(
        StatusBasket,
        on_delete=models.PROTECT,
        related_name='baskets',
        verbose_name="Статус"
    )
    date_create = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Корзина"
        verbose_name_plural = "Корзины"

    def __str__(self):
        return f"Корзина {self.user} ({self.date_create.strftime('%d.%m.%Y')})"

    def get_total_price(self):
        """Возвращает общую сумму корзины"""
        total = 0
        for item in self.items.all():
            total += item.get_subtotal()
        return total

    def clear(self):
        """Очищает корзину"""
        self.items.all().delete()

    def add_item(self, variant, quantity):
        """Добавляет позицию в корзину"""
        price = variant.product.get_discounted_price()

        item, created = PositionBasket.objects.get_or_create(
            basket=self,
            product_variant=variant,
            defaults={
                'quantity': quantity,
                'price_addition': price
            }
        )
        if not created:
            item.quantity += quantity
            item.price_addition = price
            item.save()
        return item


class PositionBasket(models.Model):
    """Позиция корзины"""
    basket = models.ForeignKey(
        Basket,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Корзина"
    )
    product_variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name='basket_positions',
        verbose_name="Вариант товара"
    )
    quantity = models.IntegerField(verbose_name="Количество")
    price_addition = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Цена на момент добавления"
    )

    class Meta:
        verbose_name = "Позиция корзины"
        verbose_name_plural = "Позиции корзин"

    def __str__(self):
        return f"{self.product_variant} x {self.quantity}"

    def get_subtotal(self):
        """Возвращает сумму по позиции"""
        return self.quantity * self.price_addition


class Order(models.Model):
    """Заказ"""
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name="Пользователь"
    )
    status = models.ForeignKey(
        StatusOrder,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name="Статус"
    )
    delivery_method = models.ForeignKey(
        DeliveryMethod,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name="Способ доставки",
        null=True,
        blank=True
    )
    date_issue = models.DateField(verbose_name="Дата оформления")

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ['-date_issue']

    def __str__(self):
        return f"Заказ #{self.id} от {self.date_issue.strftime('%d.%m.%Y')}"

    def get_total_price(self):
        """Возвращает общую сумму заказа"""
        total = 0
        for item in self.items.all():
            total += item.get_subtotal()
        return total

    def confirm(self):
        """Подтверждает заказ и списывает остатки"""
        for item in self.items.all():
            if not item.product_variant.decrease_quantity(item.quantity):
                raise Exception(f"Недостаточно товара {item.product_variant} на складе")

    def cancel(self):
        """Отменяет заказ и возвращает остатки"""
        for item in self.items.all():
            item.product_variant.quantity += item.quantity
            item.product_variant.save()


class PositionOrder(models.Model):
    """Позиция заказа"""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Заказ"
    )
    product_variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.PROTECT,
        related_name='order_positions',
        verbose_name="Вариант товара"
    )
    quantity = models.IntegerField(verbose_name="Количество")
    price_order = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Цена на момент заказа"
    )

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказов"

    def __str__(self):
        return f"{self.product_variant} x {self.quantity}"

    def get_subtotal(self):
        """Возвращает сумму по позиции"""
        return self.quantity * self.price_order