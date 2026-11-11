from django.db import models
from django.utils import timezone
from datetime import timedelta

class Category(models.Model):
    """Категория обуви (Кроссовки, Туфли, Ботинки и т.д.)"""
    name = models.CharField(max_length=100, verbose_name="Название категории")
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        verbose_name="Родительская категория"
    )

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self):
        return self.name


class Brand(models.Model):
    """Бренд обуви (Nike, Adidas, Puma и т.д.)"""
    name = models.CharField(max_length=100, verbose_name="Название бренда")
    website = models.URLField(max_length=200, blank=True, verbose_name="Сайт бренда")
    logo = models.ImageField(upload_to='brands/logos/', blank=True, null=True, verbose_name="Логотип")

    class Meta:
        verbose_name = "Бренд"
        verbose_name_plural = "Бренды"

    def __str__(self):
        return self.name


class Size(models.Model):
    """Размер обуви"""
    name = models.CharField(max_length=10, verbose_name="Размер")

    class Meta:
        verbose_name = "Размер"
        verbose_name_plural = "Размеры"
        ordering = ['name']

    def __str__(self):
        return self.name


class Color(models.Model):
    """Цвет обуви"""
    name = models.CharField(max_length=50, verbose_name="Название цвета")

    class Meta:
        verbose_name = "Цвет"
        verbose_name_plural = "Цвета"

    def __str__(self):
        return self.name


class Season(models.Model):
    """Сезон (Зима, Лето, Демисезон и т.д.)"""
    name = models.CharField(max_length=50, verbose_name="Название сезона")

    class Meta:
        verbose_name = "Сезон"
        verbose_name_plural = "Сезоны"

    def __str__(self):
        return self.name


class Style(models.Model):
    """Стиль (Классика, Спорт, Кэжуал и т.д.)"""
    name = models.CharField(max_length=50, verbose_name="Название стиля")
    description = models.TextField(blank=True, verbose_name="Описание")

    class Meta:
        verbose_name = "Стиль"
        verbose_name_plural = "Стили"

    def __str__(self):
        return self.name


class CountryOrigin(models.Model):
    """Страна производства"""
    name = models.CharField(max_length=100, verbose_name="Название страны")
    flag = models.CharField(max_length=10, blank=True, verbose_name="Флаг (код)")
    code = models.CharField(max_length=3, blank=True, verbose_name="Код страны")

    class Meta:
        verbose_name = "Страна производства"
        verbose_name_plural = "Страны производства"

    def __str__(self):
        return self.name


class TargetGroup(models.Model):
    """Целевая группа (Мужская, Женская, Унисекс, Детская)"""
    name = models.CharField(max_length=50, verbose_name="Название группы")
    description = models.TextField(blank=True, verbose_name="Описание")

    class Meta:
        verbose_name = "Целевая группа"
        verbose_name_plural = "Целевые группы"

    def __str__(self):
        return self.name


class SpecialProperties(models.Model):
    """Специальные свойства (Водонепроницаемая, Утепленная и т.д.)"""
    name = models.CharField(max_length=100, verbose_name="Название свойства")
    description = models.TextField(blank=True, verbose_name="Описание")

    class Meta:
        verbose_name = "Специальное свойство"
        verbose_name_plural = "Специальные свойства"

    def __str__(self):
        return self.name


class Material(models.Model):
    """Материал (Кожа, Текстиль, Резина и т.д.)"""
    name = models.CharField(max_length=100, verbose_name="Название материала")
    description = models.TextField(blank=True, verbose_name="Описание")

    class Meta:
        verbose_name = "Материал"
        verbose_name_plural = "Материалы"

    def __str__(self):
        return self.name


class Discount(models.Model):
    """Скидка (период действия и процент)"""
    date_start = models.DateField(verbose_name="Дата начала")
    date_end = models.DateField(verbose_name="Дата окончания")
    value = models.IntegerField(verbose_name="Размер скидки (%)")

    class Meta:
        verbose_name = "Скидка"
        verbose_name_plural = "Скидки"

    def __str__(self):
        return f"Скидка {self.value}% ({self.date_start} - {self.date_end})"

    def is_active(self):
        """Проверяет, активна ли скидка сейчас"""
        today = timezone.now().date()
        return self.date_start <= today <= self.date_end

class Product(models.Model):
    """Модель обуви (товарная позиция)"""
    name = models.CharField(max_length=200, verbose_name="Название модели")
    description = models.TextField(blank=True, verbose_name="Описание")
    photo = models.ImageField(upload_to='products/photos/', blank=True, null=True, verbose_name="Фотография")
    date_receipt = models.DateField(verbose_name="Дата поступления")
    retail_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Розничная цена"
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name="Категория"
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name="Бренд"
    )
    season = models.ForeignKey(
        Season,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name="Сезон"
    )
    style = models.ForeignKey(
        Style,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name="Стиль"
    )
    target_group = models.ForeignKey(
        TargetGroup,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name="Целевая группа"
    )
    country_origin = models.ForeignKey(
        CountryOrigin,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name="Страна производства",
        null=True,
        blank=True
    )
    special_properties = models.ForeignKey(
        SpecialProperties,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name="Специальные свойства"
    )
    discount = models.ForeignKey(
        Discount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name="Скидка"
    )

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.brand})"

    def get_total_quantity(self):
        """Возвращает общее количество всех вариантов товара"""
        total = 0
        for variant in self.variants.all():
            total += variant.quantity
        return total

    def get_availability_status(self):
        """Возвращает статус доступности: 'Много' (>5), 'Мало' (1-5), 'Нет в наличии' (0)"""
        total = self.get_total_quantity()
        if total == 0:
            return "Нет в наличии"
        elif total <= 5:
            return "Мало"
        else:
            return "Много"

    def get_discounted_price(self):
        """Возвращает цену со скидкой (если есть активная скидка или скидка 25% за отсутствие заказов)"""
        from decimal import Decimal

        if self.discount and self.discount.is_active():
            discount_multiplier = Decimal(100 - self.discount.value) / Decimal(100)
            return self.retail_price * discount_multiplier

        from orders.models import PositionOrder
        last_month = timezone.now() - timedelta(days=30)
        has_orders = PositionOrder.objects.filter(
            product_variant__product=self,
            order__date_issue__gte=last_month
        ).exists()

        if not has_orders:
            return self.retail_price * Decimal('0.75')

        return self.retail_price

    def has_orders_last_month(self):
        """Проверяет, были ли заказы на этот товар за последний месяц"""
        from orders.models import PositionOrder
        last_month = timezone.now() - timedelta(days=30)
        return PositionOrder.objects.filter(
            product_variant__product=self,
            order__date_issue__gte=last_month
        ).exists()


class ProductVariant(models.Model):
    """Вариант товара (конкретный размер и цвет)"""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants',
        verbose_name="Товар"
    )
    size = models.ForeignKey(
        Size,
        on_delete=models.PROTECT,
        related_name='variants',
        verbose_name="Размер"
    )
    color = models.ForeignKey(
        Color,
        on_delete=models.PROTECT,
        related_name='variants',
        verbose_name="Цвет"
    )
    quantity = models.IntegerField(
        default=0,
        verbose_name="Количество на складе"
    )

    class Meta:
        verbose_name = "Вариант товара"
        verbose_name_plural = "Варианты товаров"
        unique_together = ['product', 'size', 'color']

    def __str__(self):
        return f"{self.product} - {self.size}, {self.color} ({self.quantity} шт.)"

    def is_low_stock(self):
        """Проверяет, мало ли товара на складе (≤3)"""
        return self.quantity <= 3

    def decrease_quantity(self, amount):
        """Уменьшает количество товара на складе"""
        if self.quantity >= amount:
            self.quantity -= amount
            self.save()
            return True
        return False


class MaterialProduct(models.Model):
    """Связь материалов с товаром (какой материал и где используется)"""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='materials',
        verbose_name="Товар"
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name="Материал"
    )
    detail = models.CharField(
        max_length=50,
        verbose_name="Деталь обуви",
        help_text="Например: верх, подкладка, подошва"
    )

    class Meta:
        verbose_name = "Материал товара"
        verbose_name_plural = "Материалы товаров"
        unique_together = ['product', 'material', 'detail']

    def __str__(self):
        return f"{self.product} - {self.material} ({self.detail})"


class Comment(models.Model):
    """Отзыв о товаре"""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name="Товар"
    )
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name="Пользователь"
    )
    description = models.TextField(verbose_name="Текст отзыва")
    rating = models.IntegerField(
        choices=[(i, f"{i} звезда" + ("ы" if i in [2, 3, 4] else "") + ("*" if i == 5 else "")) for i in range(1, 6)],
        verbose_name="Оценка"
    )
    date_created = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ['-date_created']

    def __str__(self):
        return f"Отзыв на {self.product} от {self.user}"