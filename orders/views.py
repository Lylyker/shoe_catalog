from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.utils import timezone

from .models import (
    Basket, PositionBasket, Order, PositionOrder,
    StatusBasket, StatusOrder, DeliveryMethod,
)
from catalog.models import ProductVariant


def is_manager(user):
    return (
        user.is_staff or user.is_admin or user.is_superuser
        or (user.role and user.role.name in ('Менеджер', 'Администратор'))
    )


def is_admin(user):
    return (
        user.is_admin or user.is_superuser
        or (user.role and user.role.name == 'Администратор')
    )


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
        basket = request.user.get_active_basket()
        return render(request, self.template_name, {'basket': basket})

    def post(self, request):
        if not request.user.is_authenticated:
            messages.error(request, 'Войдите в систему')
            return redirect('users:login')

        variant_id = request.POST.get('variant_id')
        quantity = int(request.POST.get('quantity', 1))

        try:
            variant = ProductVariant.objects.get(id=variant_id)
            if variant.quantity < quantity:
                messages.error(request, 'Недостаточно товара на складе')
                return redirect('catalog:product_detail', pk=variant.product_id)

            active_status = StatusBasket.objects.get(name='Активна')
            basket, _ = Basket.objects.get_or_create(user=request.user, status=active_status)
            basket.add_item(variant, quantity)
            messages.success(request, f'Товар "{variant}" добавлен в корзину')
        except ProductVariant.DoesNotExist:
            messages.error(request, 'Товар не найден')

        return redirect('orders:cart')


class OrderCreateView(View):
    template_name = 'orders/order_create.html'

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('users:login')
        basket = request.user.get_active_basket()
        if not basket or basket.items.count() == 0:
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
        if not basket or basket.items.count() == 0:
            messages.error(request, 'Корзина пуста')
            return redirect('orders:cart')

        delivery_method_id = request.POST.get('delivery_method')
        try:
            delivery_method = DeliveryMethod.objects.get(id=delivery_method_id)
            new_status = StatusOrder.objects.get(name='Новый')
            order = Order.objects.create(
                user=request.user, status=new_status,
                delivery_method=delivery_method, date_issue=timezone.now().date(),
            )
            for basket_item in basket.items.all():
                PositionOrder.objects.create(
                    order=order,
                    product_variant=basket_item.product_variant,
                    quantity=basket_item.quantity,
                    price_order=basket_item.price_addition,
                )
                basket_item.product_variant.decrease_quantity(basket_item.quantity)
            basket.clear()
            messages.success(request, f'Заказ #{order.id} успешно оформлен!')
            return redirect('orders:order_list')
        except Exception as e:
            messages.error(request, f'Ошибка при оформлении заказа: {str(e)}')
            return redirect('orders:cart')


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
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(user__full_name__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        context['statuses'] = StatusOrder.objects.all()
        context['total_orders'] = qs.count()
        context['total_sum'] = sum(o.get_total_price() for o in qs)
        return context


class ManagerOrderDetailView(ManagerAccessMixin, DetailView):
    model = Order
    template_name = 'orders/manager_order_detail.html'
    context_object_name = 'order'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.items.select_related(
            'product_variant', 'product_variant__product',
            'product_variant__size', 'product_variant__color',
        )
        context['total'] = self.object.get_total_price()
        context['can_delete'] = is_admin(self.request.user)
        return context


class OrderItemDeleteView(AdminAccessMixin, View):
    def post(self, request, pk):
        item = get_object_or_404(PositionOrder, pk=pk)
        order = item.order
        item.product_variant.quantity += item.quantity
        item.product_variant.save()
        item.delete()
        messages.success(request, 'Позиция удалена, остаток возвращён на склад')
        return redirect('orders:manager_order_detail', pk=order.pk)