"""
Наполнение БД тестовыми данными: python manage.py seed_data
Идемпотентно — повторный запуск не создаёт дубли.
"""
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from catalog.models import (
    Category, Brand, Size, Color, Season, Style, CountryOrigin, TargetGroup,
    SpecialProperties, Material, Discount, Product, ProductVariant,
    MaterialProduct, Comment,
)
from users.models import Gender, Right, Role, User
from orders.models import (
    StatusBasket, StatusOrder, DeliveryMethod, Basket, PositionBasket,
    Order, PositionOrder,
)


def gc(model, defaults=None, **lookup):
    obj, _ = model.objects.get_or_create(defaults=defaults or {}, **lookup)
    return obj


class Command(BaseCommand):
    help = 'Наполняет базу данных тестовыми данными (справочники, товары, заказы)'

    def handle(self, *args, **options):
        today = timezone.now().date()

        # ---------- Права и роли ----------
        rights = {}
        for name in ['просмотр каталога', 'оформление заказа', 'просмотр своих заказов',
                     'управление заказами', 'управление каталогом', 'управление пользователями']:
            rights[name] = gc(Right, name=name, defaults={'description': name})

        role_buyer = gc(Role, name='Покупатель', defaults={'description': 'Базовая роль'})
        role_manager = gc(Role, name='Менеджер', defaults={'description': 'Управление заказами'})
        role_admin = gc(Role, name='Администратор', defaults={'description': 'Полный доступ'})
        role_buyer.rights.set([rights['просмотр каталога'], rights['оформление заказа'], rights['просмотр своих заказов']])
        role_manager.rights.set([rights['просмотр каталога'], rights['оформление заказа'],
                                 rights['просмотр своих заказов'], rights['управление заказами']])
        role_admin.rights.set(list(rights.values()))

        # ---------- Пол ----------
        g_m = gc(Gender, name='Мужской')
        g_f = gc(Gender, name='Женский')

        # ---------- Пользователи ----------
        admin = User.objects.filter(login='mexa').first()
        if admin:
            admin.role = role_admin
            admin.is_staff = admin.is_superuser = admin.is_admin = True
            admin.save()
        else:
            admin = User.objects.create_superuser(login='mexa', password='mexa12345',
                                                  full_name='Механиков Механик Механович', role=role_admin)

        manager = User.objects.filter(login='manager').first()
        if not manager:
            manager = User.objects.create_user(login='manager', password='manager123',
                                               full_name='Петрова Анна Сергеевна', role=role_manager,
                                               gender=g_f, phone='+79001112233')
            manager.is_staff = True
            manager.save()

        buyers = []
        for login, fio, gender in [('ivanov', 'Иванов Иван Иванович', g_m),
                                   ('petrov', 'Петров Пётр Петрович', g_m),
                                   ('sidorova', 'Сидорова Мария Ивановна', g_f)]:
            u = User.objects.filter(login=login).first()
            if not u:
                u = User.objects.create_user(login=login, password='buyer123', full_name=fio,
                                             role=role_buyer, gender=gender, phone='+79000000000')
            elif not u.role:
                u.role = role_buyer
                u.save()
            buyers.append(u)

        # ---------- Статусы и доставка ----------
        sb_active = gc(StatusBasket, name='Активна')
        gc(StatusBasket, name='Оформлена')
        gc(StatusBasket, name='Отменена')
        so_new = gc(StatusOrder, name='Новый')
        so_proc = gc(StatusOrder, name='В обработке')
        so_ship = gc(StatusOrder, name='Отправлен')
        so_done = gc(StatusOrder, name='Выполнен')
        gc(StatusOrder, name='Отменён')
        dm_courier = gc(DeliveryMethod, name='Курьер', defaults={'description': 'Доставка курьером до двери'})
        gc(DeliveryMethod, name='Самовывоз', defaults={'description': 'Самовывоз из магазина'})
        gc(DeliveryMethod, name='Почта России', defaults={'description': 'Доставка почтой'})

        # ---------- Справочники каталога ----------
        cats = {n: gc(Category, name=n) for n in ['Кроссовки', 'Туфли', 'Ботинки', 'Сапоги', 'Сандалии', 'Кеды']}
        brands = {n: gc(Brand, name=n) for n in ['Nike', 'Adidas', 'Puma', 'Reebok', 'New Balance',
                                                 'Converse', 'Vans', 'Timberland', 'Dr. Martens', 'ECCO']}
        sizes = {n: gc(Size, name=n) for n in ['36', '37', '38', '39', '40', '41', '42', '43', '44', '45']}
        colors = {n: gc(Color, name=n) for n in ['Чёрный', 'Белый', 'Красный', 'Синий', 'Серый',
                                                 'Коричневый', 'Зелёный', 'Бежевый']}
        seasons = {n: gc(Season, name=n) for n in ['Зима', 'Весна', 'Лето', 'Осень', 'Демисезон']}
        styles = {n: gc(Style, name=n) for n in ['Спорт', 'Классика', 'Кэжуал', 'Уличный']}
        groups = {n: gc(TargetGroup, name=n) for n in ['Мужчины', 'Женщины', 'Унисекс', 'Дети']}
        countries = {n: gc(CountryOrigin, name=n, defaults={'code': c}) for n, c in
                     [('Россия', 'RU'), ('Китай', 'CN'), ('Вьетнам', 'VN'), ('Италия', 'IT'),
                      ('Германия', 'DE'), ('США', 'US'), ('Великобритания', 'GB'), ('Индонезия', 'ID')]}
        props = {n: gc(SpecialProperties, name=n) for n in ['Водонепроницаемая', 'Утеплённая', 'Дышащая',
                                                            'Ортопедическая стелька', 'Нескользящая подошва']}
        mats = {n: gc(Material, name=n) for n in ['Кожа', 'Текстиль', 'Резина', 'Замша', 'Синтетика', 'ЭВА']}

        gc(Discount, value=10, defaults={'date_start': today - timedelta(days=5), 'date_end': today + timedelta(days=25)})

        # ---------- Товары (12 шт.) ----------
        # (name, brand, cat, season, style, group, country, prop, price, variants[(size,color,qty)], materials[(mat,detail)])
        products_data = [
            ('Air Max 90', 'Nike', 'Кроссовки', 'Лето', 'Спорт', 'Мужчины', 'Вьетнам', 'Дышащая', '3500.00',
             [('41', 'Чёрный', 4), ('42', 'Чёрный', 4), ('43', 'Чёрный', 2), ('42', 'Белый', 0)],
             [('Текстиль', 'верх'), ('Резина', 'подошва')]),
            ('Run', 'Adidas', 'Кроссовки', 'Лето', 'Спорт', 'Унисекс', 'Германия', 'Дышащая', '4500.00',
             [('40', 'Белый', 3), ('41', 'Белый', 5), ('42', 'Белый', 7)],
             [('Текстиль', 'верх'), ('ЭВА', 'подошва')]),
            ('Ultraboost 22', 'Adidas', 'Кроссовки', 'Демисезон', 'Спорт', 'Мужчины', 'Германия', 'Ортопедическая стелька', '12900.00',
             [('42', 'Чёрный', 6), ('43', 'Чёрный', 8), ('44', 'Синий', 3)],
             [('Текстиль', 'верх'), ('ЭВА', 'подошва')]),
            ('Suede Classic', 'Puma', 'Кеды', 'Демисезон', 'Кэжуал', 'Унисекс', 'Вьетнам', None, '6900.00',
             [('39', 'Синий', 5), ('40', 'Синий', 2), ('41', 'Красный', 0)],
             [('Замша', 'верх'), ('Резина', 'подошва')]),
            ('574 Core', 'New Balance', 'Кроссовки', 'Демисезон', 'Кэжуал', 'Унисекс', 'США', None, '8900.00',
             [('40', 'Серый', 9), ('41', 'Серый', 6), ('42', 'Серый', 4)],
             [('Замша', 'верх'), ('Текстиль', 'подкладка')]),
            ('Chuck Taylor All Star', 'Converse', 'Кеды', 'Лето', 'Уличный', 'Унисекс', 'Вьетнам', None, '5500.00',
             [('38', 'Белый', 7), ('39', 'Белый', 5), ('40', 'Чёрный', 3)],
             [('Текстиль', 'верх'), ('Резина', 'подошва')]),
            ('Old Skool', 'Vans', 'Кеды', 'Лето', 'Уличный', 'Унисекс', 'Китай', 'Нескользящая подошва', '6200.00',
             [('40', 'Чёрный', 8), ('41', 'Чёрный', 6), ('42', 'Чёрный', 2)],
             [('Кожа', 'верх'), ('Резина', 'подошва')]),
            ('1460 Smooth', 'Dr. Martens', 'Ботинки', 'Демисезон', 'Уличный', 'Унисекс', 'Великобритания', 'Водонепроницаемая', '15900.00',
             [('41', 'Чёрный', 4), ('42', 'Чёрный', 3), ('43', 'Коричневый', 1)],
             [('Кожа', 'верх'), ('Резина', 'подошва')]),
            ('6-Inch Premium', 'Timberland', 'Ботинки', 'Зима', 'Кэжуал', 'Мужчины', 'США', 'Водонепроницаемая', '18900.00',
             [('42', 'Коричневый', 5), ('43', 'Коричневый', 4), ('44', 'Коричневый', 0)],
             [('Кожа', 'верх'), ('Резина', 'подошва')]),
            ('Oxford Classic', 'ECCO', 'Туфли', 'Демисезон', 'Классика', 'Мужчины', 'Италия', 'Ортопедическая стелька', '11900.00',
             [('41', 'Чёрный', 6), ('42', 'Чёрный', 5), ('43', 'Коричневый', 2)],
             [('Кожа', 'верх'), ('Кожа', 'подкладка')]),
            ('Winter Boot Alaska', 'ECCO', 'Сапоги', 'Зима', 'Классика', 'Женщины', 'Россия', 'Утеплённая', '13900.00',
             [('37', 'Чёрный', 4), ('38', 'Чёрный', 3), ('39', 'Бежевый', 1)],
             [('Кожа', 'верх'), ('Текстиль', 'подкладка')]),
            ('Summer Sandal Wave', 'Puma', 'Сандалии', 'Лето', 'Кэжуал', 'Женщины', 'Китай', 'Дышащая', '2900.00',
             [('37', 'Белый', 10), ('38', 'Белый', 8), ('39', 'Красный', 5)],
             [('Синтетика', 'верх'), ('ЭВА', 'подошва')]),
        ]

        products = []
        for name, b, c, s, st, g, co, pr, price, variants, materials in products_data:
            product = gc(
                Product, name=name, brand=brands[b],
                defaults={
                    'description': f'{name} — качественная обувь бренда {b}. Комфорт и стиль на каждый день.',
                    'date_receipt': today - timedelta(days=15),
                    'retail_price': Decimal(price),
                    'category': cats[c], 'season': seasons[s], 'style': styles[st],
                    'target_group': groups[g], 'country_origin': countries[co],
                    'special_properties': props[pr] if pr else None,
                },
            )
            for sz, col, qty in variants:
                gc(ProductVariant, product=product, size=sizes[sz], color=colors[col], defaults={'quantity': qty})
            for mat, detail in materials:
                gc(MaterialProduct, product=product, material=mats[mat], detail=detail)
            products.append(product)

        # ---------- Отзывы ----------
        for product, user, rating, text in [
            (products[0], buyers[0], 5, 'Отличные кроссовки, удобные и лёгкие!'),
            (products[1], buyers[1], 4, 'Хорошие, но размер чуть маломерит.'),
            (products[7], buyers[2], 5, 'Классика, не промокают вообще.'),
            (products[10], buyers[2], 4, 'Тёплые сапоги, довольна покупкой.'),
        ]:
            gc(Comment, product=product, user=user, defaults={'rating': rating, 'description': text})

        # ---------- Заказы ----------
        def make_order(user, status, delivery, days_ago, items):
            order = Order.objects.filter(user=user, date_issue=today - timedelta(days=days_ago), status=status).first()
            if not order:
                order = Order.objects.create(user=user, status=status, delivery_method=delivery,
                                             date_issue=today - timedelta(days=days_ago))
                for product, qty in items:
                    variant = product.variants.filter(quantity__gt=0).first() or product.variants.first()
                    PositionOrder.objects.create(order=order, product_variant=variant, quantity=qty,
                                                 price_order=product.retail_price)
            return order

        make_order(buyers[0], so_done, dm_courier, 40, [(products[0], 1), (products[5], 1)])   # старый заказ
        make_order(buyers[1], so_ship, dm_courier, 5, [(products[1], 1)])                      # свежий заказ
        make_order(buyers[2], so_new, dm_courier, 2, [(products[7], 1), (products[10], 1)])    # свежий заказ
        make_order(buyers[0], so_proc, dm_courier, 1, [(products[2], 1)])

        # ---------- Активная корзина для ivanov ----------
        basket, _ = Basket.objects.get_or_create(user=buyers[0], status=sb_active)
        for product, qty in [(products[3], 1), (products[11], 2)]:
            variant = product.variants.filter(quantity__gt=0).first()
            if variant:
                PositionBasket.objects.get_or_create(
                    basket=basket, product_variant=variant,
                    defaults={'quantity': qty, 'price_addition': product.get_discounted_price()},
                )

        self.stdout.write(self.style.SUCCESS(
            f'Готово! Товаров: {Product.objects.count()}, вариантов: {ProductVariant.objects.count()}, '
            f'пользователей: {User.objects.count()}, заказов: {Order.objects.count()}, '
            f'отзывов: {Comment.objects.count()}'
        ))