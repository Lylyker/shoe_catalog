from django.apps import AppConfig
from django.db.models.signals import pre_save


class CoreConfig(AppConfig):
    name = 'core'
    verbose_name = 'Ядро системы'

    def ready(self):
        from . import checks  # noqa: F401 — регистрация системных проверок
        from .sanitize import sanitize_instance

        def clean_before_save(sender, instance, **kwargs):
            sanitize_instance(instance)

        pre_save.connect(clean_before_save, dispatch_uid='core_strip_surrogates')