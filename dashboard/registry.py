"""Конфигурируемый реестр сущностей: один CRUD-движок на всю админ-панель."""
from catalog.models import (Brand, Category, Color, Comment, CountryOrigin, Discount,
                            Material, MaterialProduct, Product, ProductVariant, Season,
                            SpecialProperties, Size, Style, TargetGroup)
from orders.models import DeliveryMethod, Order, StatusBasket, StatusOrder
from supply.models import (StatusSupply, StockBalance, StockMovement, Supplier, Supply,
                           Warehouse)
from users.models import Gender, Right, Role, User

from .forms import (MaterialFormSet, SupplyForm, SupplyItemFormSet, UserForm,
                    VariantFormSet, build_form, style)

AUTO_EXCLUDE = ('id',)


def E(model, title, icon, columns, *, search=(), filters=(), order=('-id',),
      write='admin', fields='__all__', exclude=AUTO_EXCLUDE, form=None,
      formsets=(), detail=False, readonly=False, group='catalog', related=()):
    return {
        'model': model, 'title': title, 'icon': icon, 'columns': columns,
        'search': list(search), 'filters': list(filters), 'order': list(order),
        'write': write, 'form': form or (None if readonly else build_form(model, fields, exclude)),
        'formsets': list(formsets), 'detail': detail, 'readonly': readonly,
        'group': group, 'related': list(related),
    }


NAME_COL = [('name', 'Название')]
REF_ORDER = ('name',)

REGISTRY = {
    'products': E(Product, 'Товары', 'shopping-bag',
                  [('name', 'Название'), ('brand', 'Бренд'), ('category', 'Категория'),
                   ('retail_price', 'Цена, ₽'), ('get_total_quantity', 'Остаток'),
                   ('get_availability_status', 'Наличие')],
                  search=['name', 'description', 'brand__name'],
                  filters=[('category', 'category', 'Категория', Category),
                           ('brand', 'brand', 'Бренд', Brand)],
                  order=('name',), formsets=[VariantFormSet, MaterialFormSet], detail=True,
                  related=[('variants', 'Размерно-цветовые варианты',
                            [('size', 'Размер'), ('color', 'Цвет'), ('quantity', 'Остаток')]),
                           ('materials', 'Материалы',
                            [('material', 'Материал'), ('detail', 'Деталь')])]),
    'variants': E(ProductVariant, 'Варианты товаров', 'list',
                  [('product', 'Товар'), ('size', 'Размер'), ('color', 'Цвет'),
                   ('quantity', 'Остаток')],
                  search=['product__name'], order=('product__name', 'size__name'),
                  filters=[('color', 'color', 'Цвет', Color), ('size', 'size', 'Размер', Size)]),
    'categories': E(Category, 'Категории', 'folder', NAME_COL + [('parent', 'Родитель')],
                    search=['name'], order=REF_ORDER),
    'brands': E(Brand, 'Бренды', 'tag', NAME_COL + [('website', 'Сайт')],
                search=['name'], order=REF_ORDER),
    'sizes': E(Size, 'Размеры', 'ruler', NAME_COL, search=['name'], order=REF_ORDER),
    'colors': E(Color, 'Цвета', 'palette', NAME_COL, search=['name'], order=REF_ORDER),
    'seasons': E(Season, 'Сезоны', 'sun', NAME_COL, search=['name'], order=REF_ORDER),
    'styles': E(Style, 'Стили', 'sparkles', NAME_COL + [('description', 'Описание')],
                search=['name'], order=REF_ORDER),
    'countries': E(CountryOrigin, 'Страны производства', 'globe',
                   NAME_COL + [('code', 'Код')], search=['name', 'code'], order=REF_ORDER),
    'groups': E(TargetGroup, 'Целевые группы', 'users', NAME_COL, search=['name'], order=REF_ORDER),
    'properties': E(SpecialProperties, 'Особые свойства', 'shield', NAME_COL,
                    search=['name'], order=REF_ORDER),
    'materials': E(Material, 'Материалы', 'layers', NAME_COL, search=['name'], order=REF_ORDER),
    'discounts': E(Discount, 'Скидки', 'percent',
                   [('value', 'Размер, %'), ('date_start', 'Начало'), ('date_end', 'Окончание'),
                    ('is_active', 'Активна')], order=('-date_start',)),
    'comments': E(Comment, 'Отзывы', 'message',
                  [('product', 'Товар'), ('user', 'Автор'), ('rating', 'Оценка'),
                   ('description', 'Текст'), ('date_created', 'Дата')],
                  search=['description', 'product__name'], order=('-date_created',),
                  write='admin', group='catalog'),

    'orders': E(Order, 'Заказы', 'cart',
                [('id', '№'), ('date_issue', 'Дата'), ('user', 'Клиент'),
                 ('status', 'Статус'), ('delivery_method', 'Доставка'),
                 ('get_total_price', 'Сумма, ₽')],
                search=['user__full_name', 'id'], order=('-date_issue', '-id'),
                write='manager', detail=True, group='orders',
                filters=[('status', 'status', 'Статус', StatusOrder)],
                related=[('items', 'Позиции заказа',
                          [('product_variant', 'Товар'), ('quantity', 'Кол-во'),
                           ('price_order', 'Цена, ₽'), ('get_subtotal', 'Сумма, ₽')])]),
    'order-statuses': E(StatusOrder, 'Статусы заказов', 'flag', NAME_COL,
                        search=['name'], order=REF_ORDER, group='orders'),
    'basket-statuses': E(StatusBasket, 'Статусы корзин', 'flag', NAME_COL,
                         search=['name'], order=REF_ORDER, group='orders'),
    'delivery': E(DeliveryMethod, 'Способы доставки', 'truck',
                  NAME_COL + [('description', 'Описание')],
                  search=['name'], order=REF_ORDER, group='orders'),

    'users': E(User, 'Пользователи', 'user',
               [('login', 'Логин'), ('full_name', 'ФИО'), ('role', 'Роль'),
                ('email', 'E-mail'), ('is_active', 'Активен'), ('is_staff', 'Админка')],
               search=['login', 'full_name', 'email'], order=('login',),
               form=style(UserForm), group='users',
               filters=[('role', 'role', 'Роль', Role)]),
    'roles': E(Role, 'Роли', 'key', NAME_COL + [('description', 'Описание')],
               search=['name'], order=REF_ORDER, group='users'),
    'rights': E(Right, 'Права', 'lock', NAME_COL + [('description', 'Описание')],
                search=['name'], order=REF_ORDER, group='users'),
    'genders': E(Gender, 'Пол', 'user', NAME_COL, search=['name'], order=REF_ORDER, group='users'),

    'suppliers': E(Supplier, 'Поставщики', 'building',
                   NAME_COL + [('contact_person', 'Контакт'), ('phone', 'Телефон'),
                               ('inn', 'ИНН'), ('is_active', 'Активен')],
                   search=['name', 'contact_person', 'inn'], order=REF_ORDER, group='supply'),
    'warehouses': E(Warehouse, 'Склады', 'warehouse',
                    NAME_COL + [('address', 'Адрес'), ('is_default', 'По умолчанию'),
                                ('get_total_quantity', 'Единиц товара')],
                    search=['name', 'address'], order=REF_ORDER, group='supply'),
    'supplies': E(Supply, 'Поставки', 'inbox',
                  [('number', 'Номер'), ('date_supply', 'Дата'), ('supplier', 'Поставщик'),
                   ('warehouse', 'Склад'), ('status', 'Статус'),
                   ('get_total_quantity', 'Единиц'), ('get_total_price', 'Сумма, ₽')],
                  search=['number', 'supplier__name', 'note'], order=('-date_supply', '-id'),
                  form=style(SupplyForm), formsets=[SupplyItemFormSet], detail=True,
                  group='supply',
                  filters=[('status', 'status', 'Статус', StatusSupply),
                           ('warehouse', 'warehouse', 'Склад', Warehouse)],
                  related=[('items', 'Позиции поставки',
                            [('product_variant', 'Товар'), ('quantity', 'Кол-во'),
                             ('purchase_price', 'Закупка, ₽'), ('get_subtotal', 'Сумма, ₽')])]),
    'supply-statuses': E(StatusSupply, 'Статусы поставок', 'flag',
                         NAME_COL + [('code', 'Код')], search=['name', 'code'],
                         order=REF_ORDER, group='supply'),
    'stock': E(StockBalance, 'Остатки на складах', 'boxes',
               [('warehouse', 'Склад'), ('product_variant', 'Товар'), ('quantity', 'Количество')],
               search=['product_variant__product__name'], order=('warehouse__name',),
               readonly=True, group='supply',
               filters=[('warehouse', 'warehouse', 'Склад', Warehouse)]),
    'movements': E(StockMovement, 'Журнал движений', 'history',
                   [('created_at', 'Дата'), ('product_variant', 'Товар'), ('warehouse', 'Склад'),
                    ('quantity', 'Изменение'), ('get_reason_display', 'Основание'),
                    ('supply', 'Поставка'), ('order', 'Заказ')],
                   search=['product_variant__product__name'], order=('-created_at', '-id'),
                   readonly=True, group='supply',
                   filters=[('reason', 'reason', 'Основание', None)]),
}

GROUPS = [
    ('catalog', 'Каталог', ['products', 'variants', 'categories', 'brands', 'sizes', 'colors',
                            'seasons', 'styles', 'countries', 'groups', 'properties',
                            'materials', 'discounts', 'comments']),
    ('orders', 'Заказы', ['orders', 'delivery', 'order-statuses', 'basket-statuses']),
    ('supply', 'Склад и поставки', ['supplies', 'suppliers', 'warehouses', 'stock',
                                    'movements', 'supply-statuses']),
    ('users', 'Пользователи', ['users', 'roles', 'rights', 'genders']),
]


def get(slug):
    cfg = REGISTRY.get(slug)
    if cfg is None:
        from django.http import Http404
        raise Http404('Неизвестный раздел: %s' % slug)
    return dict(cfg, slug=slug)