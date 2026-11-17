from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


def is_manager(user):
    return bool(user.is_authenticated and (
        user.is_staff or user.is_admin or user.is_superuser
        or (user.role and user.role.name in ('Менеджер', 'Администратор'))))


def is_admin(user):
    return bool(user.is_authenticated and (
        user.is_admin or user.is_superuser
        or (user.role and user.role.name == 'Администратор')))


class PanelMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = 'users:login'

    def test_func(self):
        return is_manager(self.request.user)


class AdminWriteMixin(PanelMixin):
    def test_func(self):
        return is_admin(self.request.user)