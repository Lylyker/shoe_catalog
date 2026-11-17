from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic import DetailView, ListView, View

from catalog.models import ProductVariant
from supply.services import StockError, consume_stock, return_stock_for_order

from .models import (Basket, DeliveryMethod, Order, PositionOrder, StatusBasket,
                     StatusOrder)


def is_manager(user):
    return (user.is_staff or user.is_admin or user.is_superuser
            or (user.role and user.role.name in ('Менеджер', 'Администратор')))


def is_admin(user):
    return (user.is_admin or user.is_superuser
            or (user.role and user.role.name == 'Администратор'))


class ManagerAccessMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = 'users:login'

    def test_func(self):
        return is_manager(self.request.user)


class AdminAccessMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = 'users:login'

    def test_func(self):
        return is_admin(self.request.user)


class CartView(View):
    template_name = 'orders/cart.html'

    def get(self, request):
        if not request.user.is_authenticated:
            messages.error(request, 'Войдите в систему')
            return redirect('users:login')
        return render(request, self.template_name,
                      {'basket': request.user.get_active_basket()})

    def post(self, request):
        if not request.user.is_authenticated:
            messages.error(request, 'Войдите в систему')
            return redirect('users:login')

        variant_id = request.POST.get('variant_id')
        try:
            quantity = int(request.POST.get('quantity', 1))
        except (TypeError, ValueError):
            quantity = 1

        try:
            variant = ProductVariant.objects.get(id=variant_id)
        except ProductVariant.DoesNotExist:
            messages.error(request, 'Товар не найден')
            return redirect('catalog:catalog')

        if quantity < 1:
            messages.error(request, 'Количество должно быть не меньше 1')
            return redirect('catalog:product_detail', pk=variant.product_id)
        if variant.quantity < quantity:
            messages.error(request, 'Недостаточно товара на складе')
            return redirect('catalog:product_detail', pk=variant.product_id)

        active_status, _ = StatusBasket.objects.get_or_create(name='Активна')
        basket, _ = Basket.objects.get_or_create(user=request.user, status=active_status)
        basket.add_item(variant, quantity)
        messages.success(request, f'Товар "{variant}" добавлен в корзину')
        return redirect('orders:cart')


class OrderCreateView(View):
    template_name = 'orders/order_create.html'

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('users:login')
        basket = request.user.get_active_basket()
        if not basket or not basket.items.exists():
            messages.error(request, 'Корзина пуста')
            return redirect('orders:cart')
        return render(request, self.template_name, {
            'basket': basket,
            'delivery_methods': DeliveryMethod.objects.all(),
        })

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('users:login')
        basket = request.user.get_active_basket()
        if not basket or not basket.items.exists():
            messages.error(request, 'Корзина пуста')
            return redirect('orders:cart')

        try:
            with transaction.atomic():
                delivery_method = DeliveryMethod.objects.get(
                    id=request.POST.get('delivery_method'))
                new_status, _ = StatusOrder.objects.get_or_create(name='Новый')
                order = Order.objects.create(
                    user=request.user, status=new_status,
                    delivery_method=delivery_method, date_issue=timezone.localdate())

                for basket_item in basket.items.select_related('product_variant'):
                    variant = basket_item.product_variant
                    PositionOrder.objects.create(
                        order=order, product_variant=variant,
                        quantity=basket_item.quantity,
                        price_order=basket_item.price_addition)
                    consume_stock(variant, basket_item.quantity,
                                  order=order, user=request.user)
                basket.clear()
        except DeliveryMethod.DoesNotExist:
            messages.error(request, 'Выберите способ доставки')
            return redirect('orders:order_create')
        except StockError as exc:
            messages.error(request, str(exc))
            return redirect('orders:cart')

        messages.success(request, f'Заказ #{order.id} успешно оформлен!')
        return redirect('orders:order_list')


class OrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'orders/order_list.html'
    context_object_name = 'orders'
    paginate_by = 10
    login_url = 'users:login'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-date_issue')


class OrderDetailView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = 'orders/order_detail.html'
    context_object_name = 'order'
    login_url = 'users:login'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


class ManagerOrderListView(ManagerAccessMixin, ListView):
    model = Order
    template_name = 'orders/manager_order_list.html'
    context_object_name = 'orders'
    paginate_by = 20

    def get_queryset(self):
        qs = Order.objects.select_related('user', 'status', 'delivery_method').order_by('-date_issue')
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status_id=status)
        query = self.request.GET.get('q', '').strip()
        if query:
            qs = qs.filter(user__full_name__icontains=query)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        context['statuses'] = StatusOrder.objects.all()
        context['total_orders'] = qs.count()
        context['total_sum'] = sum(order.get_total_price() for order in qs)
        return context


class ManagerOrderDetailView(ManagerAccessMixin, DetailView):
    model = Order
    template_name = 'orders/manager_order_detail.html'
    context_object_name = 'order'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.items.select_related(
            'product_variant', 'product_variant__product',
            'product_variant__size', 'product_variant__color')
        context['total'] = self.object.get_total_price()
        context['can_delete'] = is_admin(self.request.user)
        return context


class OrderItemDeleteView(AdminAccessMixin, View):
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
            return redirect('orders:manager_order_detail', pk=order.pk)
        messages.success(request, 'Позиция удалена, остаток возвращён на склад')
        return redirect('orders:manager_order_detail', pk=order.pk)