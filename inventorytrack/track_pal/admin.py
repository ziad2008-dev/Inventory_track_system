from django.contrib import admin
from .models import company, UserProfile, warehouse, product, warehouse_stock, SellableProduct, RecipeItem, InventoryTransaction, StockOrder, Sale, SaleItem

@admin.register(company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'manager', 'created_at')
    search_fields = ('name',)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'company')
    list_select_related = ('user', 'company')
    search_fields = ('user__username', 'company__name')
    autocomplete_fields = ('company',)   # works with CompanyAdmin search_fields

@admin.register(warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'company', 'location', 'type', 'created_at')
    list_filter = ('company', 'type')
    search_fields = ('name', 'location')

@admin.register(product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'company', 'sku', 'unit', 'pricing')
    list_filter = ('company', 'unit')
    search_fields = ('name', 'sku')

@admin.register(warehouse_stock)
class WarehouseStockAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'warehouse', 'quantity', 'last_updated')
    list_filter = ('warehouse',)
    search_fields = ('product__name',)


class RecipeItemInline(admin.TabularInline):
    model = RecipeItem
    extra = 1

@admin.register(SellableProduct)
class SellableProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'company', 'sku', 'selling_price', 'created_at')
    list_filter = ('company',)
    search_fields = ('name', 'sku')
    inlines = [RecipeItemInline]


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'transaction_type', 'product', 'warehouse', 'quantity', 'timestamp', 'created_by')
    list_filter = ('transaction_type', 'warehouse')
    search_fields = ('product__name',)


@admin.register(StockOrder)
class StockOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'direction', 'product', 'warehouse', 'quantity', 'status', 'party', 'shipping_method', 'vehicle_count', 'created_at')
    list_filter = ('direction', 'status', 'warehouse')
    search_fields = ('product__name', 'party')


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'company', 'warehouse', 'total_price', 'created_at', 'created_by')
    list_filter = ('company', 'warehouse')
    inlines = [SaleItemInline]