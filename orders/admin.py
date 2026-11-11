from django.contrib import admin
from .models import (
    StatusBasket, StatusOrder, DeliveryMethod,
    Basket, PositionBasket, Order, PositionOrder
)


@admin.register(StatusBasket)
class StatusBasketAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(StatusOrder)
class StatusOrderAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(DeliveryMethod)
class DeliveryMethodAdmin(admin.ModelAdmin):
    list_display = ('name',)


class PositionBasketInline(admin.TabularInline):
    model = PositionBasket
    extra = 0


@admin.register(Basket)
class BasketAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'date_create', 'get_total_price')
    list_filter = ('status',)
    search_fields = ('user__full_name',)
    inlines = [PositionBasketInline]

    def get_total_price(self, obj):
        return obj.get_total_price()

    get_total_price.short_description = 'Сумма'


class PositionOrderInline(admin.TabularInline):
    model = PositionOrder
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'date_issue', 'status', 'delivery_method', 'get_total_price')
    list_filter = ('status', 'date_issue')
    search_fields = ('user__full_name',)
    inlines = [PositionOrderInline]

    def get_total_price(self, obj):
        return obj.get_total_price()

    get_total_price.short_description = 'Сумма'