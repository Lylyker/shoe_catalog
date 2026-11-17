from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from catalog.models import Product, ProductVariant
from orders.models import Order, PositionOrder, StatusOrder
from supply.models import StatusSupply, StockBalance, StockMovement, Supply
from supply.services import (StockError, add_stock, cancel_supply, post_supply,
                             remove_stock, return_stock_for_order)
from users.models import User

from .access import AdminWriteMixin, PanelMixin, is_admin
from .forms import OrderItemAddForm, StockAdjustForm, style
from .registry import GROUPS, REGISTRY, get
from .templatetags.dash import get_attr


def nav(slug=None):
    return [{'title': t, 'items': [{'slug': s, 'title': REGISTRY[s]['title'],
                                    'active': s == slug} for s in slugs]}
            for _, t, slugs in GROUPS]


def can_write(request, cfg):
    if cfg['readonly']:
        return False
    return is_admin(request.user) if cfg['write'] == 'admin' else True


def apply_formset_style(formset):
    for form in formset.forms:
        for field in form.fields.values():
            w = field.widget
            cls = 'form-check-input' if w.__class__.__name__ == 'CheckboxInput' else (
                'form-select' if 'Select' in w.__class__.__name__ else 'form-control')
            w.attrs['class'] = cls


class DashboardHome(PanelMixin, TemplateView):
    template_name = 'dashboard/home.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        low = ProductVariant.objects.select_related('product', 'size', 'color').filter(
            quantity__lte=3).order_by('quantity')[:12]
        ctx.update({
            'nav': nav(), 'is_admin': is_admin(self.request.user),
            'stats': [
                ('Товаров', Product.objects.count(), ''),
                ('Заказов', Order.objects.count(), 'b2'),
                ('Выручка, ₽', Order.objects.aggregate(
                    s=Sum('items__price_order'))['s'] or 0, 'b3'),
                ('Поставок', Supply.objects.count(), 'b4'),
                ('Дефицитных позиций', low.count(), 'b5'),
            ],
            'recent_orders': Order.objects.select_related('user', 'status').order_by('-id')[:8],
            'drafts': Supply.objects.filter(status__code='draft').select_related('supplier')[:6],
            'low': low,
        })
        return ctx


class EntityList(PanelMixin, View):
    def get(self, request, slug):
        cfg = get(slug)
        model = cfg['model']
        qs = model.objects.all()

        term = request.GET.get('q', '').strip()
        if term and cfg['search']:
            query = Q()
            for field in cfg['search']:
                query |= Q(**{field + '__icontains': term})
            qs = qs.filter(query)

        active = {}
        filters = []
        for param, field, label, source in cfg['filters']:
            value = request.GET.get(param, '')
            if source is None:
                choices = model._meta.get_field(field).choices
            else:
                choices = [(o.pk, str(o)) for o in source.objects.all()]
            filters.append({'param': param, 'label': label, 'choices': choices, 'value': value})
            if value:
                qs = qs.filter(**{field: value})
                active[param] = value

        sort = request.GET.get('sort', '')
        names = {f.name for f in model._meta.fields}
        if sort.lstrip('-') in names:
            qs = qs.order_by(sort)
        else:
            qs = qs.order_by(*cfg['order'])
            sort = ''

        try:
            page = max(1, int(request.GET.get('page', 1)))
        except ValueError:
            page = 1
        per = 20
        total = qs.count()
        pages = max(1, (total + per - 1) // per)
        page = min(page, pages)
        rows = list(qs[(page - 1) * per: page * per])

        keep = {k: v for k, v in request.GET.items() if v and k != 'page'}
        return render(request, 'dashboard/list.html', {
            'cfg': cfg, 'nav': nav(slug), 'rows': rows, 'total': total,
            'columns': cfg['columns'], 'filters': filters, 'term': term, 'sort': sort,
            'page': page, 'pages': pages, 'keep': keep,
            'page_range': range(max(1, page - 2), min(pages, page + 2) + 1),
            'can_write': can_write(request, cfg),
            'has_prev': page > 1, 'has_next': page < pages,
        })


class EntityDetail(PanelMixin, View):
    def get(self, request, slug, pk):
        cfg = get(slug)
        if not cfg['detail']:
            raise Http404
        obj = get_object_or_404(cfg['model'], pk=pk)
        blocks = []
        for rel, title, cols in cfg['related']:
            manager = getattr(obj, rel)
            blocks.append({'title': title, 'columns': cols,
                           'rows': list(manager.select_related()[:200]),
                           'is_order_items': slug == 'orders'})
        fields = [(label, get_attr(obj, key)) for key, label in cfg['columns']]
        actions = []
        if slug == 'supplies':
            if obj.is_draft:
                actions = [('post', 'Провести поставку', 'btn-success'),
                           ('edit', 'Редактировать', 'btn-primary'),
                           ('delete', 'Удалить черновик', 'btn-danger')]
            elif obj.is_posted:
                actions = [('cancel', 'Отменить поставку', 'btn-warn')]
        elif slug == 'orders':
            actions = [('edit', 'Изменить заказ', 'btn-primary')]
            if is_admin(request.user):
                actions.append(('delete', 'Удалить заказ', 'btn-danger'))
        else:
            actions = [('edit', 'Редактировать', 'btn-primary')]
            if is_admin(request.user):
                actions.append(('delete', 'Удалить', 'btn-danger'))
        return render(request, 'dashboard/detail.html', {
            'cfg': cfg, 'nav': nav(slug), 'obj': obj, 'fields': fields, 'blocks': blocks,
            'actions': actions if can_write(request, cfg) else [],
            'add_form': OrderItemAddForm() if slug == 'orders' else None,
            'can_write': can_write(request, cfg),
        })


class EntityFormBase(PanelMixin, View):
    create = False

    def dispatch(self, request, *args, **kwargs):
        self.cfg = get(kwargs['slug'])
        if not can_write(request, self.cfg):
            messages.error(request, 'Недостаточно прав для изменения этого раздела.')
            return redirect('dashboard:list', slug=kwargs['slug'])
        if self.cfg['form'] is None:
            raise Http404
        self.obj = None
        if not self.create:
            self.obj = get_object_or_404(self.cfg['model'], pk=kwargs['pk'])
            if self.cfg['slug'] == 'supplies' and not self.obj.is_draft:
                messages.error(request, 'Редактировать можно только поставку в статусе «Черновик».')
                return redirect('dashboard:detail', slug='supplies', pk=self.obj.pk)
        return super().dispatch(request, *args, **kwargs)

    def build(self, data=None, files=None):
        form = self.cfg['form'](data, files, instance=self.obj)
        sets = []
        for factory in self.cfg['formsets']:
            fs = factory(data, files, instance=self.obj,
                         prefix=factory.model._meta.model_name)
            apply_formset_style(fs)
            sets.append({'fs': fs, 'title': factory.model._meta.verbose_name_plural,
                         'empty': fs.empty_form})
        style(form.__class__)
        return form, sets

    def get(self, request, slug, pk=None):
        form, sets = self.build()
        return self.render(form, sets)

    def post(self, request, slug, pk=None):
        form, sets = self.build(request.POST, request.FILES)
        valid = form.is_valid()
        for item in sets:
            valid = item['fs'].is_valid() and valid
        if not valid:
            return self.render(form, sets)
        with transaction.atomic():
            obj = form.save(commit=False)
            if self.cfg['slug'] == 'supplies' and self.create:
                obj.status = StatusSupply.objects.get(code='draft')
                obj.created_by = request.user
            if self.cfg['slug'] == 'users':
                pwd = form.cleaned_data.get('new_password')
                if pwd:
                    obj.set_password(pwd)
                    obj.must_change_password = True
                elif not obj.pk:
                    obj.set_password(None)
            obj.save()
            form.save_m2m()
            for item in sets:
                item['fs'].instance = obj
                item['fs'].save()
        messages.success(request, f'{"Создано" if self.create else "Сохранено"}: {obj}')
        if self.cfg['detail']:
            return redirect('dashboard:detail', slug=slug, pk=obj.pk)
        return redirect('dashboard:list', slug=slug)

    def render(self, form, sets):
        multipart = any(f.widget.__class__.__name__ == 'ClearableFileInput'
                        for f in form.fields.values())
        return render(self.request, 'dashboard/form.html', {
            'cfg': self.cfg, 'nav': nav(self.cfg['slug']), 'form': form, 'sets': sets,
            'obj': self.obj, 'create': self.create, 'multipart': multipart,
        })


class EntityCreate(EntityFormBase):
    create = True


class EntityUpdate(EntityFormBase):
    create = False


class EntityDelete(AdminWriteMixin, View):
    def get(self, request, slug, pk):
        cfg = get(slug)
        obj = get_object_or_404(cfg['model'], pk=pk)
        return render(request, 'dashboard/confirm_delete.html',
                      {'cfg': cfg, 'nav': nav(slug), 'obj': obj})

    def post(self, request, slug, pk):
        cfg = get(slug)
        obj = get_object_or_404(cfg['model'], pk=pk)
        if slug == 'supplies' and not obj.is_draft:
            messages.error(request, 'Удалять можно только черновики поставок.')
            return redirect('dashboard:detail', slug=slug, pk=pk)
        if slug == 'orders':
            try:
                with transaction.atomic():
                    for item in obj.items.select_related('product_variant'):
                        return_stock_for_order(item.product_variant, item.quantity,
                                               order=obj, user=request.user)
                    obj.delete()
            except StockError as exc:
                messages.error(request, str(exc))
                return redirect('dashboard:detail', slug=slug, pk=pk)
            messages.success(request, 'Заказ удалён, остатки возвращены на склады.')
            return redirect('dashboard:list', slug=slug)
        label = str(obj)
        try:
            obj.delete()
        except Exception as exc:
            messages.error(request, f'Удаление невозможно: объект используется ({exc.__class__.__name__}).')
            return redirect('dashboard:list', slug=slug)
        messages.success(request, f'Удалено: {label}')
        return redirect('dashboard:list', slug=slug)


class BulkDelete(AdminWriteMixin, View):
    def post(self, request, slug):
        cfg = get(slug)
        if slug in ('orders', 'supplies', 'stock', 'movements'):
            messages.error(request, 'Массовое удаление для этого раздела отключено.')
            return redirect('dashboard:list', slug=slug)
        ids = request.POST.getlist('ids')
        if not ids:
            messages.warning(request, 'Ничего не выбрано.')
            return redirect('dashboard:list', slug=slug)
        deleted, failed = 0, 0
        for obj in cfg['model'].objects.filter(pk__in=ids):
            try:
                obj.delete()
                deleted += 1
            except Exception:
                failed += 1
        messages.success(request, f'Удалено записей: {deleted}. Пропущено (используются): {failed}.')
        return redirect('dashboard:list', slug=slug)


class SupplyAction(AdminWriteMixin, View):
    def post(self, request, pk, action):
        supply = get_object_or_404(Supply, pk=pk)
        try:
            if action == 'post':
                post_supply(supply, request.user)
                messages.success(request, f'Поставка {supply.number} проведена, остатки увеличены.')
            elif action == 'cancel':
                cancel_supply(supply, request.user)
                messages.success(request, f'Поставка {supply.number} отменена, остатки списаны.')
            else:
                raise Http404
        except StockError as exc:
            messages.error(request, str(exc))
        return redirect('dashboard:detail', slug='supplies', pk=pk)


class OrderItemAdd(PanelMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        form = OrderItemAddForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Проверьте вариант товара и количество.')
            return redirect('dashboard:detail', slug='orders', pk=pk)
        variant = form.cleaned_data['product_variant']
        qty = form.cleaned_data['quantity']
        price = form.cleaned_data['price_order'] or variant.product.get_discounted_price()
        try:
            with transaction.atomic():
                item, created = PositionOrder.objects.get_or_create(
                    order=order, product_variant=variant,
                    defaults={'quantity': qty, 'price_order': price})
                if not created:
                    item.quantity += qty
                    item.save(update_fields=['quantity'])
                from supply.services import consume_stock
                consume_stock(variant, qty, order=order, user=request.user)
        except StockError as exc:
            messages.error(request, str(exc))
            return redirect('dashboard:detail', slug='orders', pk=pk)
        messages.success(request, f'Позиция добавлена: {variant} × {qty}.')
        return redirect('dashboard:detail', slug='orders', pk=pk)


class OrderItemRemove(PanelMixin, View):
    def post(self, request, pk):
        item = get_object_or_404(PositionOrder, pk=pk)
        order = item.order
        try:
            with transaction.atomic():
                return_stock_for_order(item.product_variant, item.quantity,
                                       order=order, user=request.user)
                item.delete()
        except StockError as exc:
            messages.error(request, str(exc))
            return redirect('dashboard:detail', slug='orders', pk=order.pk)
        messages.success(request, 'Позиция удалена, остаток возвращён на склад.')
        return redirect('dashboard:detail', slug='orders', pk=order.pk)


class StockAdjust(AdminWriteMixin, View):
    def get(self, request, pk):
        balance = get_object_or_404(StockBalance, pk=pk)
        return render(request, 'dashboard/form.html', {
            'cfg': get('stock'), 'nav': nav('stock'), 'form': StockAdjustForm(),
            'sets': [], 'obj': balance, 'create': False, 'multipart': False,
            'custom_title': f'Корректировка остатка: {balance}',
        })

    def post(self, request, pk):
        balance = get_object_or_404(StockBalance, pk=pk)
        form = StockAdjustForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Укажите целое изменение количества.')
            return redirect('dashboard:stock-adjust', pk=pk)
        delta = form.cleaned_data['delta']
        try:
            if delta > 0:
                add_stock(balance.product_variant, balance.warehouse, delta,
                          reason='manual', user=request.user)
            elif delta < 0:
                remove_stock(balance.product_variant, balance.warehouse, -delta,
                             reason='manual', user=request.user)
            else:
                messages.warning(request, 'Изменение равно нулю.')
                return redirect('dashboard:list', slug='stock')
        except StockError as exc:
            messages.error(request, str(exc))
            return redirect('dashboard:stock-adjust', pk=pk)
        messages.success(request, 'Остаток скорректирован, движение записано в журнал.')
        return redirect('dashboard:list', slug='stock')