from django.db import models
from django.conf import settings

class company(models.Model):
    name=models.CharField(max_length=100)
    manager=models.CharField(max_length=100,blank=True,null=True)
    created_at=models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    user=models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    company=models.ForeignKey(company, on_delete=models.CASCADE, related_name='members')

    def __str__(self):
        return f'{self.user.username} → {self.company.name}'


class warehouse(models.Model):
    WAREHOUSE_TYPE_CHOICES = [
        ('raw_material', 'Raw Material'),
        ('finished_goods', 'Finished Goods'),
        ('consumables', 'Consumables'),
        ('OTHERS', 'OTHERS'),
    ]
    name=models.CharField(max_length=100)
    company=models.ForeignKey(company,on_delete=models.CASCADE,related_name='warehouses')
    location=models.CharField(max_length=100)
    type=models.CharField(max_length=20, choices=WAREHOUSE_TYPE_CHOICES)
    created_at=models.DateTimeField(auto_now_add=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='warehouses_created')

    def __str__(self):
        return f'{self.name} - {self.company.name}'


class product(models.Model):
    Unit_CHOICES = [
        ('kg', 'Kilogram'),
        ('gm', 'Gram'),
        ('litre', 'Litre'),
        ('pcs', 'Pieces'),
        ('box', 'Box'),
        ('OTHERS', 'OTHERS'),]
    company=models.ForeignKey(company,on_delete=models.CASCADE,related_name='products')
    sku=models.CharField(max_length=100,unique=True,blank=True,null=True)
    name=models.CharField(max_length=100)
    description=models.TextField(blank=True,null=True)
    unit=models.CharField(max_length=20,choices=Unit_CHOICES)
    minimum_stock_level=models.PositiveIntegerField(default=0)
    alert_stock_level=models.PositiveIntegerField(default=0)
    pricing=models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="cost price per unit")
    created_at=models.DateTimeField(auto_now_add=True)
    expiry_date=models.DateField(blank=True, null=True)
    net_weight=models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    gross_weight=models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    volume_cbm=models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    class Meta:
        unique_together = ('company', 'name')

    def __str__(self):
        return self.name


class warehouse_stock(models.Model):
    warehouse=models.ForeignKey(warehouse,on_delete=models.CASCADE,related_name='stocks')
    product=models.ForeignKey(product,on_delete=models.CASCADE,related_name='stocks')
    quantity=models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_updated=models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('warehouse', 'product')

    def __str__(self):
        return f'{self.product.name} @ {self.warehouse.name}: {self.quantity}'


# ============================================================
# Sellable product (finished good) + its recipe of raw materials
# Cost is computed live from each ingredient's product.pricing.
# ============================================================
class SellableProduct(models.Model):
    company=models.ForeignKey(company, on_delete=models.CASCADE, related_name='sellable_products')
    name=models.CharField(max_length=100)
    sku=models.CharField(max_length=100, blank=True, null=True)
    selling_price=models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True,
                                       help_text="price you sell this finished product for")
    # The stockable product that represents this finished good. Auto-created
    # so producing a batch can add finished units to warehouse stock.
    finished_product=models.OneToOneField('product', on_delete=models.SET_NULL,
                                           null=True, blank=True, related_name='sellable_source')
    created_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('company', 'name')

    def __str__(self):
        return self.name


class RecipeItem(models.Model):
    """One ingredient line: this finished product needs `quantity`
    of `ingredient` (a raw material product). Quantity is expressed
    in the ingredient's own unit, and cost = quantity * ingredient.pricing."""
    sellable=models.ForeignKey(SellableProduct, on_delete=models.CASCADE, related_name='recipe_items')
    ingredient=models.ForeignKey(product, on_delete=models.PROTECT, related_name='used_in')
    quantity=models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                 help_text="how much of this ingredient, in the ingredient's own unit")

    def __str__(self):
        return f'{self.quantity} {self.ingredient.unit} {self.ingredient.name} → {self.sellable.name}'


class InventoryTransaction(models.Model):
    """A stock movement. Creating one (via the API) atomically updates
    warehouse_stock:
      stock_in   -> add quantity
      stock_out  -> subtract quantity (blocked if not enough)
      adjustment -> set stock to exactly quantity
    quantity is always positive; transaction_type decides direction."""
    TRANSACTION_TYPE_CHOICES = [
        ('stock_in', 'Stock In'),
        ('stock_out', 'Stock Out'),
        ('adjustment', 'Adjustment'),
    ]
    warehouse=models.ForeignKey(warehouse, on_delete=models.CASCADE, related_name='transactions')
    product=models.ForeignKey(product, on_delete=models.CASCADE, related_name='transactions')
    quantity=models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type=models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    note=models.CharField(max_length=200, blank=True, null=True)
    timestamp=models.DateTimeField(auto_now_add=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                 null=True, blank=True, related_name='transactions_created')

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.transaction_type} {self.quantity} {self.product.name} @ {self.warehouse.name}'


class StockOrder(models.Model):
    """An incoming (purchase) or outgoing (delivery) order that moves through
    a status lifecycle. Stock only changes when status becomes 'delivered':
      incoming delivered -> stock += quantity
      outgoing delivered -> stock -= quantity (blocked if short)
    Cancelling a delivered order reverses the stock change.
    `stock_applied` guards against double-applying."""
    DIRECTION_CHOICES = [
        ('incoming', 'Incoming (from supplier)'),
        ('outgoing', 'Outgoing (to customer)'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    company=models.ForeignKey(company, on_delete=models.CASCADE, related_name='orders')
    direction=models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    warehouse=models.ForeignKey(warehouse, on_delete=models.CASCADE, related_name='orders')
    product=models.ForeignKey(product, on_delete=models.CASCADE, related_name='orders')
    quantity=models.DecimalField(max_digits=12, decimal_places=2)
    status=models.CharField(max_length=12, choices=STATUS_CHOICES, default='pending')
    party=models.CharField(max_length=150, blank=True, null=True,
                           help_text="supplier name (incoming) or customer name (outgoing)")
    note=models.CharField(max_length=200, blank=True, null=True)

    # ---- shipping / logistics (descriptive only, no stock effect) ----
    SHIPPING_METHOD_CHOICES = [
        ('sea', 'Sea'),
        ('ground', 'Ground'),
        ('air', 'Air'),
    ]
    VEHICLE_TYPE_CHOICES = [
        ('truck', 'Truck'),
        ('ship', 'Ship'),
        ('plane', 'Plane'),
        ('container', 'Container'),
    ]
    shipping_method=models.CharField(max_length=10, choices=SHIPPING_METHOD_CHOICES, blank=True, null=True)
    vehicle_type=models.CharField(max_length=12, choices=VEHICLE_TYPE_CHOICES, blank=True, null=True)
    vehicle_count=models.PositiveIntegerField(blank=True, null=True,
                                              help_text="number of trucks / ships / containers")
    carrier=models.CharField(max_length=150, blank=True, null=True, help_text="shipping company")
    tracking_number=models.CharField(max_length=120, blank=True, null=True)
    estimated_arrival=models.DateField(blank=True, null=True)

    stock_applied=models.BooleanField(default=False)  # has this order's stock change been applied?
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                 null=True, blank=True, related_name='orders_created')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.direction} {self.quantity} {self.product.name} [{self.status}]'