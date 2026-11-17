from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View

from .forms import LoginForm, RegisterForm, ProfileForm, PasswordChangeForm
from .models import User, Role
from orders.models import Order


def safe_next(request, fallback='catalog:catalog'):
    """Защита от open redirect при возврате по ?next=."""
    nxt = request.GET.get('next') or request.POST.get('next')
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return nxt
    return fallback


class CustomLoginView(View):
    """Вход в систему: логин + пароль (или только логин в режиме ДЭ)."""
    template_name = 'users/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('catalog:catalog')
        form = LoginForm(require_password=settings.REQUIRE_PASSWORD)
        return render(request, self.template_name, {
            'form': form,
            'require_password': settings.REQUIRE_PASSWORD,
            'next': request.GET.get('next', ''),
        })

    def post(self, request):
        form = LoginForm(request.POST, require_password=settings.REQUIRE_PASSWORD)
        if form.is_valid():
            user = form.user
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f'Добро пожаловать, {user.full_name}!')
            if user.must_change_password:
                messages.warning(request, 'Вы используете временный пароль. Задайте новый.')
                return redirect('users:password_change')
            return redirect(safe_next(request))
        return render(request, self.template_name, {
            'form': form,
            'require_password': settings.REQUIRE_PASSWORD,
            'next': request.POST.get('next', ''),
        })


class RegisterView(View):
    """Регистрация нового пользователя с паролем и ролью «Покупатель»."""
    template_name = 'users/register.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('catalog:catalog')
        return render(request, self.template_name, {'form': RegisterForm()})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            buyer_role, _ = Role.objects.get_or_create(
                name='Покупатель',
                defaults={'description': 'Базовая роль для всех зарегистрированных пользователей'}
            )
            user = User.objects.create_user(
                login=form.cleaned_data['login'],
                password=form.cleaned_data['password1'],
                full_name=form.cleaned_data['full_name'],
                email=form.cleaned_data.get('email', ''),
                role=buyer_role,
            )
            messages.success(request, f'Пользователь {user.full_name} зарегистрирован. Теперь войдите.')
            return redirect('users:login')
        return render(request, self.template_name, {'form': form})


class PasswordChangeView(LoginRequiredMixin, View):
    """Смена пароля (в том числе принудительная смена временного)."""
    template_name = 'users/password_change.html'
    login_url = 'users:login'

    def get(self, request):
        return render(request, self.template_name, {
            'form': PasswordChangeForm(request.user),
            'forced': request.user.must_change_password,
        })

    def post(self, request):
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            request.user.set_password(form.cleaned_data['password1'])
            request.user.must_change_password = False
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Пароль успешно изменён.')
            return redirect('users:profile')
        return render(request, self.template_name, {
            'form': form,
            'forced': request.user.must_change_password,
        })


class ProfileView(LoginRequiredMixin, View):
    """Личный кабинет: данные, заказы, корзина."""
    login_url = 'users:login'
    template_name = 'users/profile.html'

    def get(self, request):
        orders = Order.objects.filter(user=request.user).order_by('-date_issue')[:10]
        return render(request, self.template_name, {
            'user': request.user,
            'orders': orders,
            'basket': request.user.get_active_basket(),
            'form': ProfileForm(instance=request.user),
        })

    def post(self, request):
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Данные обновлены!')
            return redirect('users:profile')
        orders = Order.objects.filter(user=request.user).order_by('-date_issue')[:10]
        return render(request, self.template_name, {
            'user': request.user,
            'orders': orders,
            'basket': request.user.get_active_basket(),
            'form': form,
        })


class LogoutView(View):
    """Выход из системы."""
    def get(self, request):
        logout(request)
        messages.success(request, 'Вы вышли из системы')
        return redirect('users:login')