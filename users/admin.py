from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Role, Right, Gender


@admin.register(Gender)
class GenderAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Right)
class RightAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name',)
    filter_horizontal = ('rights',)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('login', 'full_name', 'role', 'is_active', 'is_staff', 'is_superuser')
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser')
    search_fields = ('login', 'full_name')
    filter_horizontal = ()
    filter_vertical = ()

    fieldsets = (
        (None, {'fields': ('login', 'password')}),
        ('Персональная информация', {'fields': ('full_name', 'gender', 'icon', 'phone', 'delivery_address')}),
        ('Права доступа', {'fields': ('role', 'is_active', 'is_admin', 'is_staff', 'is_superuser')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('login', 'full_name', 'password1', 'password2', 'role', 'is_staff', 'is_superuser'),
        }),
    )

    ordering = ('login',)