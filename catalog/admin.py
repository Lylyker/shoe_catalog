from django.contrib import admin
from .models import (
    Category, Brand, Size, Color, Season, Style,
    CountryOrigin, TargetGroup, SpecialProperties,
    Material, Discount, Product, ProductVariant,
    MaterialProduct, Comment
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent')
    search_fields = ('name',)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'website')
    search_fields = ('name',)


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Style)
class StyleAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(CountryOrigin)
class CountryOriginAdmin(admin.ModelAdmin):
    list_display = ('name', 'flag', 'code')
    search_fields = ('name',)


@admin.register(TargetGroup)
class TargetGroupAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(SpecialProperties)
class SpecialPropertiesAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ('date_start', 'date_end', 'value')
    list_filter = ('date_start', 'date_end')


class MaterialProductInline(admin.TabularInline):
    """Материалы товара редактируются прямо в карточке товара"""
    model = MaterialProduct
    extra = 1


class ProductVariantInline(admin.TabularInline):
    """Варианты (размер/цвет/остаток) редактируются прямо в карточке товара"""
    model = ProductVariant
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'category', 'retail_price', 'get_total_quantity', 'date_receipt')
    list_filter = ('category', 'brand', 'season', 'style')
    search_fields = ('name', 'description')
    inlines = [MaterialProductInline, ProductVariantInline]

    def get_total_quantity(self, obj):
        return obj.get_total_quantity()

    get_total_quantity.short_description = 'Общее кол-во'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'date_created')
    list_filter = ('rating',)
    search_fields = ('product__name', 'user__full_name')