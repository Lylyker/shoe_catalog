import django_filters
from django.db.models import Q
from .models import Product, Category, Brand, Season, Style, Size, Color, CountryOrigin, TargetGroup, SpecialProperties


class ProductFilter(django_filters.FilterSet):
    """Фильтр для каталога товаров"""

    # Фильтр по категории
    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.all(),
        label="Категория",
        empty_label="Все"
    )

    # Фильтр по бренду
    brand = django_filters.ModelChoiceFilter(
        queryset=Brand.objects.all(),
        label="Бренд",
        empty_label="Все"
    )

    # Фильтр по сезону
    season = django_filters.ModelChoiceFilter(
        queryset=Season.objects.all(),
        label="Сезон",
        empty_label="Все"
    )

    # Фильтр по стилю
    style = django_filters.ModelChoiceFilter(
        queryset=Style.objects.all(),
        label="Стиль",
        empty_label="Все"
    )

    # Фильтр по размеру
    size = django_filters.ModelChoiceFilter(
        field_name='variants__size',
        queryset=Size.objects.all(),
        label="Размер",
        empty_label="Все",
        distinct=True
    )

    # Фильтр по цвету
    color = django_filters.ModelChoiceFilter(
        field_name='variants__color',
        queryset=Color.objects.all(),
        label="Цвет",
        empty_label="Все",
        distinct=True
    )

    # Фильтр по стране производства
    country_origin = django_filters.ModelChoiceFilter(
        queryset=CountryOrigin.objects.all(),
        label="Страна",
        empty_label="Все"
    )

    # Фильтр по целевой группе
    target_group = django_filters.ModelChoiceFilter(
        queryset=TargetGroup.objects.all(),
        label="Целевая группа",
        empty_label="Все"
    )

    # Фильтр по специальным свойствам
    special_properties = django_filters.ModelChoiceFilter(
        queryset=SpecialProperties.objects.all(),
        label="Особенности",
        empty_label="Все"
    )

    # Фильтр по цене (от)
    price_min = django_filters.NumberFilter(
        field_name='retail_price',
        lookup_expr='gte',
        label="Цена от"
    )

    # Фильтр по цене (до)
    price_max = django_filters.NumberFilter(
        field_name='retail_price',
        lookup_expr='lte',
        label="Цена до"
    )

    # Полнотекстовый поиск
    search = django_filters.CharFilter(
        method='filter_search',
        label="Поиск"
    )

    def filter_search(self, queryset, name, value):
        """Кастомный метод поиска по названию и описанию"""
        if value:
            return queryset.filter(
                Q(name__icontains=value) | Q(description__icontains=value)
            )
        return queryset

    class Meta:
        model = Product
        fields = ['category', 'brand', 'season', 'style', 'size', 'color',
                  'country_origin', 'target_group', 'special_properties']