"""Бизнес-логика складского учёта.

Все операции атомарны и блокируют строки остатков (select_for_update),
чтобы параллельные заказы не приводили к рассинхронизации.
"""
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from catalog.models import ProductVariant
from .models import StatusSupply, StockBalance, StockMovement, Supply, Warehouse


class StockError(Exception):
    """Ошибка складской операции (нехватка остатка, неверный статус и т. п.)."""


def get_default_warehouse():
    return Warehouse.objects.filter(is_active=True).order_by('-is_default', 'id').first()


def _lock_variant(variant):
    return ProductVariant.objects.select_for_update().get(pk=variant.pk)


def sync_variant(variant):
    """Пересчитывает агрегированный остаток варианта по всем складам."""
    total = StockBalance.objects.filter(product_variant=variant).aggregate(
        s=Sum('quantity'))['s'] or 0
    if variant.quantity != total:
        variant.quantity = total
        variant.save(update_fields=['quantity'])
    return total


def _move(variant, warehouse, delta, reason, supply=None, order=None, user=None):
    balance, _ = StockBalance.objects.select_for_update().get_or_create(
        warehouse=warehouse, product_variant=variant, defaults={'quantity': 0})
    new_qty = balance.quantity + delta
    if new_qty < 0:
        raise StockError(f'Недостаточно остатка на складе «{warehouse}»: '
                         f'есть {balance.quantity}, требуется {abs(delta)}.')
    balance.quantity = new_qty
    balance.save(update_fields=['quantity'])
    StockMovement.objects.create(
        product_variant=variant, warehouse=warehouse, quantity=delta, reason=reason,
        supply=supply, order=order, user=user)
    return balance


@transaction.atomic
def add_stock(variant, warehouse, quantity, *, reason='supply',
              supply=None, order=None, user=None):
    """Приход товара на конкретный склад."""
    if quantity <= 0:
        raise StockError('Количество прихода должно быть положительным.')
    variant = _lock_variant(variant)
    _move(variant, warehouse, quantity, reason, supply, order, user)
    sync_variant(variant)


@transaction.atomic
def remove_stock(variant, warehouse, quantity, *, reason='manual',
                 supply=None, order=None, user=None):
    """Расход товара с конкретного склада."""
    if quantity <= 0:
        raise StockError('Количество расхода должно быть положительным.')
    variant = _lock_variant(variant)
    _move(variant, warehouse, -quantity, reason, supply, order, user)
    sync_variant(variant)


@transaction.atomic
def consume_stock(variant, quantity, *, order=None, user=None):
    """Списание под заказ: распределяется по складам от большего остатка к меньшему."""
    if quantity <= 0:
        raise StockError('Количество списания должно быть положительным.')
    variant = _lock_variant(variant)

    # Самовосстановление: если складской учёт по варианту ещё не заведён,
    # переносим текущий остаток на склад по умолчанию.
    if not StockBalance.objects.filter(product_variant=variant).exists() and variant.quantity:
        warehouse = get_default_warehouse()
        if warehouse is None:
            raise StockError('Не заведён ни один активный склад. '
                             'Выполните: python manage.py init_stock')
        StockBalance.objects.create(warehouse=warehouse, product_variant=variant,
                                    quantity=variant.quantity)

    balances = list(StockBalance.objects.select_for_update().filter(
        product_variant=variant, quantity__gt=0).order_by('-quantity', 'id'))
    available = sum(b.quantity for b in balances)
    if available < quantity:
        raise StockError(f'Недостаточно товара «{variant}» на складах: '
                         f'доступно {available}, требуется {quantity}.')

    left = quantity
    for balance in balances:
        take = min(balance.quantity, left)
        _move(variant, balance.warehouse, -take, 'order', order=order, user=user)
        left -= take
        if not left:
            break
    sync_variant(variant)


@transaction.atomic
def return_stock_for_order(variant, quantity, *, order=None, user=None):
    """Возврат по заказу строго на те склады, откуда было списание."""
    if quantity <= 0:
        raise StockError('Количество возврата должно быть положительным.')
    variant = _lock_variant(variant)

    movements = StockMovement.objects.filter(
        order=order, product_variant=variant, reason='order').order_by('id')
    returned = StockMovement.objects.filter(
        order=order, product_variant=variant, reason='return').aggregate(
        s=Sum('quantity'))['s'] or 0
    left = min(quantity, sum(-m.quantity for m in movements) - returned)

    for movement in movements:
        if left <= 0:
            break
        already = StockMovement.objects.filter(
            order=order, product_variant=variant, reason='return',
            warehouse=movement.warehouse).aggregate(s=Sum('quantity'))['s'] or 0
        capacity = -movement.quantity - already
        take = min(capacity, left)
        if take > 0:
            _move(variant, movement.warehouse, take, 'return', order=order, user=user)
            left -= take

    if left > 0:
        warehouse = get_default_warehouse()
        if warehouse is None:
            raise StockError('Не заведён ни один активный склад для возврата.')
        _move(variant, warehouse, left, 'return', order=order, user=user)
    sync_variant(variant)


@transaction.atomic
def post_supply(supply, user=None):
    """Проведение поставки: приход всех позиций на склад поставки."""
    supply = Supply.objects.select_for_update().get(pk=supply.pk)
    if not supply.is_draft:
        raise StockError('Провести можно только поставку в статусе «Черновик».')
    items = list(supply.items.select_related('product_variant'))
    if not items:
        raise StockError('Поставка не содержит позиций.')

    for item in items:
        add_stock(item.product_variant, supply.warehouse, item.quantity,
                  reason='supply', supply=supply, user=user)

    supply.status = StatusSupply.objects.get(code='posted')
    supply.posted_by = user
    supply.posted_at = timezone.now()
    supply.save(update_fields=['status', 'posted_by', 'posted_at'])
    return supply


@transaction.atomic
def cancel_supply(supply, user=None):
    """Отмена проведённой поставки: обратное списание, если товар ещё не продан."""
    supply = Supply.objects.select_for_update().get(pk=supply.pk)
    if not supply.is_posted:
        raise StockError('Отменить можно только проведённую поставку.')

    items = list(supply.items.select_related('product_variant'))
    for item in items:
        balance = StockBalance.objects.filter(
            warehouse=supply.warehouse, product_variant=item.product_variant).first()
        if balance is None or balance.quantity < item.quantity:
            raise StockError(
                f'Отмена невозможна: по позиции «{item.product_variant}» остаток на складе '
                f'«{supply.warehouse}» меньше поставленного количества — часть товара уже продана.')

    for item in items:
        remove_stock(item.product_variant, supply.warehouse, item.quantity,
                     reason='cancel', supply=supply, user=user)

    supply.status = StatusSupply.objects.get(code='cancelled')
    supply.save(update_fields=['status'])
    return supply