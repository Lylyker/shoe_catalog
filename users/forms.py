from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import User


class LoginForm(forms.Form):
    """Вход: логин + пароль (пароль отключается настройкой REQUIRE_PASSWORD)."""
    login = forms.CharField(
        label='Логин', max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'autofocus': True,
                                      'placeholder': 'Введите логин'})
    )
    password = forms.CharField(
        label='Пароль', required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control',
                                          'placeholder': 'Введите пароль'})
    )

    def __init__(self, *args, require_password=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.require_password = require_password
        self.fields['password'].required = require_password
        self.user = None

    def clean(self):
        data = super().clean()
        login = (data.get('login') or '').strip()
        password = data.get('password')

        if not login:
            raise ValidationError('Введите логин.')

        try:
            user = User.objects.get(login=login)
        except User.DoesNotExist:
            raise ValidationError('Пользователь с таким логином не найден. '
                                  'Проверьте раскладку клавиатуры или зарегистрируйтесь.')

        if not user.is_active:
            raise ValidationError('Учётная запись отключена. Обратитесь к администратору.')

        if self.require_password:
            if not user.has_usable_password():
                raise ValidationError('Для этой учётной записи пароль не задан. '
                                      'Обратитесь к администратору для сброса пароля.')
            if not user.check_password(password):
                raise ValidationError('Неверный пароль. Проверьте раскладку и регистр символов.')

        self.user = user
        return data


class RegisterForm(forms.Form):
    """Регистрация с паролем."""
    login = forms.CharField(
        label='Логин', max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'autofocus': True})
    )
    full_name = forms.CharField(
        label='ФИО', max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control',
                                      'placeholder': 'Иванов Иван Иванович'})
    )
    email = forms.EmailField(
        label='E-mail', required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    password1 = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    password2 = forms.CharField(
        label='Повторите пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    def clean_login(self):
        login = self.cleaned_data['login'].strip()
        if len(login) < 3:
            raise ValidationError('Логин должен содержать не менее 3 символов.')
        if not all(c.isalnum() or c in '._-' for c in login):
            raise ValidationError('Логин может содержать только латиницу, цифры и символы . _ -')
        if User.objects.filter(login__iexact=login).exists():
            raise ValidationError('Пользователь с таким логином уже существует.')
        return login

    def clean(self):
        data = super().clean()
        p1, p2 = data.get('password1'), data.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Пароли не совпадают.')
        elif p1:
            probe = User(login=data.get('login', ''), full_name=data.get('full_name', ''))
            try:
                validate_password(p1, user=probe)
            except ValidationError as e:
                self.add_error('password1', e)
        return data


class ProfileForm(forms.ModelForm):
    """Редактирование личных данных."""
    class Meta:
        model = User
        fields = ['full_name', 'email', 'phone', 'delivery_address']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control',
                                            'placeholder': '+7 (900) 000-00-00'}),
            'delivery_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class PasswordChangeForm(forms.Form):
    """Смена пароля: старый + новый дважды."""
    old_password = forms.CharField(
        label='Текущий пароль', required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    password1 = forms.CharField(
        label='Новый пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    password2 = forms.CharField(
        label='Повторите новый пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields['old_password'].required = user.has_usable_password()

    def clean_old_password(self):
        old = self.cleaned_data.get('old_password')
        if self.user.has_usable_password() and not self.user.check_password(old):
            raise ValidationError('Текущий пароль указан неверно.')
        return old

    def clean(self):
        data = super().clean()
        p1, p2 = data.get('password1'), data.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Пароли не совпадают.')
        elif p1:
            if data.get('old_password') and p1 == data['old_password']:
                self.add_error('password1', 'Новый пароль должен отличаться от текущего.')
            try:
                validate_password(p1, user=self.user)
            except ValidationError as e:
                self.add_error('password1', e)
        return data