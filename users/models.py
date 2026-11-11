from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager


class Gender(models.Model):
    """Пол пользователя"""
    name = models.CharField(max_length=20, verbose_name="Название")

    class Meta:
        verbose_name = "Пол"
        verbose_name_plural = "Пол"

    def __str__(self):
        return self.name


class Right(models.Model):
    """Право доступа"""
    name = models.CharField(max_length=100, verbose_name="Название права")
    description = models.TextField(blank=True, verbose_name="Описание")

    class Meta:
        verbose_name = "Право"
        verbose_name_plural = "Права"

    def __str__(self):
        return self.name


class Role(models.Model):
    """Роль пользователя (Покупатель, Менеджер, Администратор)"""
    name = models.CharField(max_length=50, verbose_name="Название роли")
    description = models.TextField(blank=True, verbose_name="Описание")
    rights = models.ManyToManyField(
        Right,
        blank=True,
        related_name='roles',
        verbose_name="Права"
    )

    class Meta:
        verbose_name = "Роль"
        verbose_name_plural = "Роли"

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    """Менеджер пользователей с корректным хешированием пароля"""
    use_in_migrations = True

    def _create_user(self, login, password, **extra_fields):
        if not login:
            raise ValueError('Поле login обязательно для заполнения')
        user = self.model(login=login, **extra_fields)
        user.set_password(password)  # ВАЖНО: хешируем пароль, а не пишем как есть
        user.save(using=self._db)
        return user

    def create_user(self, login, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('is_admin', False)
        return self._create_user(login, password, **extra_fields)

    def create_superuser(self, login, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_admin', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Суперпользователь должен иметь is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Суперпользователь должен иметь is_superuser=True.')

        return self._create_user(login, password, **extra_fields)


class User(AbstractBaseUser):
    """Пользователь системы"""
    login = models.CharField(max_length=50, unique=True, verbose_name="Логин")
    full_name = models.CharField(max_length=150, verbose_name="ФИО")
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name="Роль"
    )
    gender = models.ForeignKey(
        Gender,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name="Пол"
    )
    icon = models.ImageField(
        upload_to='users/icons/',
        blank=True,
        null=True,
        verbose_name="Иконка/Аватар"
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name="Телефон")
    delivery_address = models.TextField(blank=True, verbose_name="Адрес доставки")

    is_active = models.BooleanField(default=True, verbose_name="Активен")
    is_admin = models.BooleanField(default=False, verbose_name="Администратор (роль)")
    is_staff = models.BooleanField(default=False, verbose_name="Доступ в админку")
    is_superuser = models.BooleanField(default=False, verbose_name="Суперпользователь")
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name="Дата регистрации")

    objects = UserManager()

    USERNAME_FIELD = 'login'
    REQUIRED_FIELDS = ['full_name']

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return self.full_name or self.login

    def get_active_basket(self):
        """Возвращает активную корзину пользователя"""
        from orders.models import Basket
        return Basket.objects.filter(user=self, status__name='Активна').first()

    def get_orders(self):
        """Возвращает все заказы пользователя"""
        from orders.models import Order
        return Order.objects.filter(user=self)

    def has_perm(self, perm, obj=None):
        if not self.is_active:
            return False
        if self.is_superuser or self.is_staff or self.is_admin:
            return True
        if self.role:
            return self.role.rights.filter(name=perm).exists()
        return False

    def has_module_perms(self, app_label):
        return self.is_active and (self.is_superuser or self.is_staff or self.is_admin)