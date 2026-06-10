from rest_framework import serializers
from datetime import date, timedelta
from .models import (company, SellableProduct, RecipeItem, warehouse,
                     product, warehouse_stock, InventoryTransaction)


# ---------------------------------------------------------------
# Warehouse
# ---------------------------------------------------------------
class warehouseSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = warehouse
        fields = ['id', 'company', 'company_name', 'name', 'location', 'type',
                  'created_by', 'created_by_username', 'created_at']
        read_only_fields = ['id', 'company', 'created_by', 'created_at']


# ---------------------------------------------------------------
# Product  (all computed fields read-only; every Decimal wrapped in float)
# ---------------------------------------------------------------
class productSerializer(serializers.ModelSerializer):
    total_stock    = serializers.SerializerMethodField()
    total_value    = serializers.SerializerMethodField()
    expiry_status  = serializers.SerializerMethodField()
    days_to_expiry = serializers.SerializerMethodField()

    class Meta:
        model = product
        fields = [
            'id', 'company', 'sku', 'name', 'description', 'unit',
            'minimum_stock_level', 'alert_stock_level', 'pricing',
            'expiry_date', 'net_weight', 'gross_weight', 'volume_cbm',
            'created_at',
            'total_stock', 'total_value', 'expiry_status', 'days_to_expiry',
        ]
        read_only_fields = ['id', 'company', 'created_at']

    def get_total_stock(self, obj):
        return float(sum(float(s.quantity) for s in obj.stocks.all()))

    def get_total_value(self, obj):
        if obj.pricing is None:
            return None
        total = sum(float(s.quantity) for s in obj.stocks.all())
        return round(float(obj.pricing) * total, 2)

    def get_days_to_expiry(self, obj):
        if not obj.expiry_date:
            return None
        return (obj.expiry_date - date.today()).days

    def get_expiry_status(self, obj):
        if not obj.expiry_date:
            return None
        days = (obj.expiry_date - date.today()).days
        if days < 0:
            return 'expired'
        if days <= 30:
            return 'expiring_soon'
        return 'ok'


# ---------------------------------------------------------------
# Warehouse stock (one product's quantity in one warehouse)
# ---------------------------------------------------------------
class warehouseStockSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    product_name   = serializers.CharField(source='product.name', read_only=True)
    product_unit   = serializers.CharField(source='product.unit', read_only=True)
    product_sku    = serializers.CharField(source='product.sku', read_only=True)

    alert_status   = serializers.SerializerMethodField()
    expiry_status  = serializers.SerializerMethodField()
    days_to_expiry = serializers.SerializerMethodField()
    line_value     = serializers.SerializerMethodField()

    class Meta:
        model = warehouse_stock
        fields = ['id', 'warehouse', 'warehouse_name', 'product', 'product_name',
                  'product_sku', 'product_unit', 'quantity', 'last_updated',
                  'alert_status', 'expiry_status', 'days_to_expiry', 'line_value']
        read_only_fields = ['id', 'last_updated', 'alert_status',
                            'expiry_status', 'days_to_expiry', 'line_value']

    def get_days_to_expiry(self, obj):
        ed = obj.product.expiry_date
        if not ed:
            return None
        return (ed - date.today()).days

    def get_alert_status(self, obj):
        p = obj.product
        qty = float(obj.quantity)
        if qty <= p.minimum_stock_level:
            return 'critical'
        if qty <= p.alert_stock_level:
            return 'low'
        return 'healthy'

    def get_expiry_status(self, obj):
        ed = obj.product.expiry_date
        if not ed:
            return None
        days = (ed - date.today()).days
        if days < 0:
            return 'expired'
        if days <= 30:
            return 'expiring_soon'
        return 'ok'

    def get_line_value(self, obj):
        if obj.product.pricing is None:
            return None
        return round(float(obj.product.pricing) * float(obj.quantity), 2)


# ============================================================
# Sellable product (finished good) with recipe + live costing
# ============================================================
class RecipeItemSerializer(serializers.ModelSerializer):
    ingredient_name  = serializers.CharField(source='ingredient.name', read_only=True)
    ingredient_unit  = serializers.CharField(source='ingredient.unit', read_only=True)
    ingredient_price = serializers.DecimalField(source='ingredient.pricing', max_digits=10,
                                                decimal_places=2, read_only=True)
    line_cost = serializers.SerializerMethodField()

    class Meta:
        model = RecipeItem
        fields = ['id', 'ingredient', 'ingredient_name', 'ingredient_unit',
                  'ingredient_price', 'quantity', 'line_cost']
        read_only_fields = ['id', 'ingredient_name', 'ingredient_unit',
                            'ingredient_price', 'line_cost']

    def get_line_cost(self, obj):
        price = obj.ingredient.pricing
        if price is None:
            return None
        return round(float(price) * float(obj.quantity), 2)


class SellableProductSerializer(serializers.ModelSerializer):
    recipe_items = RecipeItemSerializer(many=True, required=False)

    total_cost     = serializers.SerializerMethodField()
    profit         = serializers.SerializerMethodField()
    margin_percent = serializers.SerializerMethodField()

    class Meta:
        model = SellableProduct
        fields = ['id', 'company', 'name', 'sku', 'selling_price', 'created_at',
                  'recipe_items', 'total_cost', 'profit', 'margin_percent',
                  'finished_product']
        read_only_fields = ['id', 'company', 'created_at',
                            'total_cost', 'profit', 'margin_percent',
                            'finished_product']

    def get_total_cost(self, obj):
        total = 0.0
        for item in obj.recipe_items.all():
            price = item.ingredient.pricing
            if price is not None:
                total += float(price) * float(item.quantity)
        return round(total, 2)

    def get_profit(self, obj):
        if obj.selling_price is None:
            return None
        return round(float(obj.selling_price) - self.get_total_cost(obj), 2)

    def get_margin_percent(self, obj):
        if obj.selling_price is None or float(obj.selling_price) == 0:
            return None
        profit = float(obj.selling_price) - self.get_total_cost(obj)
        return round(profit / float(obj.selling_price) * 100, 1)

    def create(self, validated_data):
        items = validated_data.pop('recipe_items', [])
        sellable = SellableProduct.objects.create(**validated_data)
        # auto-create a stockable product to represent this finished good,
        # so production can add finished units to warehouse stock
        comp = sellable.company
        fp = product.objects.create(
            company=comp,
            name=f"[Finished] {sellable.name}",
            unit='pcs',
            pricing=sellable.selling_price,
        )
        sellable.finished_product = fp
        sellable.save()
        for item in items:
            RecipeItem.objects.create(sellable=sellable, **item)
        return sellable

    def update(self, instance, validated_data):
        items = validated_data.pop('recipe_items', None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if items is not None:
            instance.recipe_items.all().delete()
            for item in items:
                RecipeItem.objects.create(sellable=instance, **item)
        return instance


# ============================================================
# Inventory transaction (stock movement)
# ============================================================
class InventoryTransactionSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    product_name   = serializers.CharField(source='product.name', read_only=True)
    product_unit   = serializers.CharField(source='product.unit', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = InventoryTransaction
        fields = ['id', 'warehouse', 'warehouse_name', 'product', 'product_name',
                  'product_unit', 'quantity', 'transaction_type', 'note',
                  'timestamp', 'created_by', 'created_by_username']
        read_only_fields = ['id', 'timestamp', 'created_by']

    def validate_quantity(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return value