from django.contrib import admin

from .models import (StatusSupply, StockBalance, StockMovement, Supplier,
                     Supply, SupplyItem, Warehouse)

class SupplyItemInline(admin.TabularInline):
    model = SupplyItem
    extra = 1
    autocomplete_fields = ('product_variant',)


@admin.register(StatusSupply)
class StatusSupplyAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'email', 'inn', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'contact_person', 'phone', 'inn')


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'is_default', 'is_active', 'get_total_quantity')
    list_filter = ('is_active', 'is_default')
    search_fields = ('name', 'address')


@admin.register(Supply)
class SupplyAdmin(admin.ModelAdmin):
    list_display = ('number', 'date_supply', 'supplier', 'warehouse', 'status',
                    'get_total_quantity', 'get_total_price', 'posted_at')
    list_filter = ('status', 'warehouse', 'supplier', 'date_supply')
    search_fields = ('number', 'supplier__name', 'note')
    date_hierarchy = 'date_supply'
    inlines = (SupplyItemInline,)
    readonly_fields = ('number', 'created_by', 'created_at', 'posted_by', 'posted_at')


@admin.register(StockBalance)
class StockBalanceAdmin(admin.ModelAdmin):
    list_display = ('product_variant', 'warehouse', 'quantity')
    list_filter = ('warehouse',)
    search_fields = ('product_variant__product__name',)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'product_variant', 'warehouse', 'quantity',
                    'reason', 'supply', 'order', 'user')
    list_filter = ('reason', 'warehouse', 'created_at')
    search_fields = ('product_variant__product__name',)
    readonly_fields = tuple(f.name for f in StockMovement._meta.fields)

    def has_add_permission(self, request):
        return False