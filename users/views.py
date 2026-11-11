from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import User, Role
from orders.models import Order


class CustomLoginView(View):
    """Авторизация по логину без пароля (требование ДЭ)"""
    template_name = 'users/login.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        login_input = request.POST.get('login', '').strip()
        if not login_input:
            messages.error(request, 'Введите логин')
            return render(request, self.template_name)

        try:
            user = User.objects.get(login=login_input)
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f'Добро пожаловать, {user.full_name}!')
            return redirect('catalog:catalog')
        except User.DoesNotExist:
            messages.error(request, 'Пользователь не найден')
            return render(request, self.template_name)


class RegisterView(View):
    """Регистрация нового пользователя (только логин)"""
    template_name = 'users/register.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        login_input = request.POST.get('login', '').strip()
        full_name = request.POST.get('full_name', '').strip()

        if not login_input:
            messages.error(request, 'Введите логин')
            return render(request, self.template_name)

        if not full_name:
            messages.error(request, 'Введите ФИО')
            return render(request, self.template_name)

        if User.objects.filter(login=login_input).exists():
            messages.error(request, 'Пользователь с таким логином уже существует')
            return render(request, self.template_name)

        buyer_role, _ = Role.objects.get_or_create(
            name='Покупатель',
            defaults={'description': 'Базовая роль для всех зарегистрированных пользователей'}
        )

        user = User.objects.create_user(
            login=login_input,
            full_name=full_name,
            role=buyer_role
        )

        messages.success(request, f'Пользователь {user.full_name} зарегистрирован! Теперь войдите.')
        return redirect('users:login')


class ProfileView(LoginRequiredMixin, View):
    """Личный кабинет пользователя"""
    login_url = 'users:login'
    template_name = 'users/profile.html'

    def get(self, request):
        orders = Order.objects.filter(user=request.user).order_by('-date_issue')[:10]
        basket = request.user.get_active_basket()
        context = {
            'user': request.user,
            'orders': orders,
            'basket': basket,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        delivery_address = request.POST.get('delivery_address', '').strip()

        if full_name:
            request.user.full_name = full_name
        request.user.phone = phone
        request.user.delivery_address = delivery_address
        request.user.save()

        messages.success(request, 'Данные обновлены!')
        return redirect('users:profile')


class LogoutView(View):
    """Выход из системы"""
    def get(self, request):
        logout(request)
        messages.success(request, 'Вы вышли из системы')
        return redirect('users:login')