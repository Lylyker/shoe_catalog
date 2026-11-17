"""
Выдача временных паролей пользователям без пароля:
    python manage.py init_passwords
    python manage.py init_passwords --password Start12345
"""
from django.core.management.base import BaseCommand
from users.models import User


class Command(BaseCommand):
    help = 'Задаёт временные пароли пользователям, у которых пароль не установлен'

    def add_arguments(self, parser):
        parser.add_argument('--password', help='Единый временный пароль для всех')
        parser.add_argument('--all', action='store_true', help='Перебрать всех, включая тех, у кого пароль есть')

    def handle(self, *args, **options):
        qs = User.objects.all() if options['all'] else User.objects.filter(password='')
        fixed = 0
        for user in qs:
            if not options['all'] and user.has_usable_password():
                continue
            temp = options['password'] or f'{user.login}12345'
            user.set_password(temp)
            user.must_change_password = True
            user.save()
            fixed += 1
            self.stdout.write(f'{user.login:<15} → временный пароль: {temp}')
        self.stdout.write(self.style.SUCCESS(
            f'Готово. Обработано учётных записей: {fixed}. '
            f'При первом входе система потребует сменить пароль.'
        ))