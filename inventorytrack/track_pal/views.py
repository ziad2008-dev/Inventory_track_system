from django.shortcuts import render
from .models import company, SellableProduct, RecipeItem, warehouse, product, warehouse_stock, InventoryTransaction, StockOrder, Sale, SaleItem
from .serializers import SellableProductSerializer, warehouseSerializer, productSerializer, warehouseStockSerializer, InventoryTransactionSerializer, StockOrderSerializer, SaleSerializer
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from django.views.generic import TemplateView
from django.db import transaction as db_transaction
from decimal import Decimal


def _user_company(request):
    """Return the company the logged-in user belongs to, or None."""
    user = request.user
    if not user.is_authenticated:
        return None
    profile = getattr(user, 'profile', None)
    return profile.company if profile else None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    user = request.user
    comp = _user_company(request)
    display_name = (user.get_full_name() or "").strip() or user.username
    return Response({
        "username": user.username,
        "name": display_name,
        "first_name": user.first_name,
        "company": comp.name if comp else None,
        "company_id": comp.id if comp else None,
        "manager": comp.manager if comp else None,
        "default_sales_warehouse": comp.default_sales_warehouse_id if comp else None,
        "default_sales_warehouse_name": (comp.default_sales_warehouse.name
                                          if comp and comp.default_sales_warehouse else None),
    })


class WarehouseViewSet(viewsets.ModelViewSet):
    serializer_class = warehouseSerializer

    def get_queryset(self):
        comp = _user_company(self.request)
        if comp is None:
            return warehouse.objects.none()
        return warehouse.objects.filter(company=comp)

    def perform_create(self, serializer):
        comp = _user_company(self.request)
        if comp is None:
            raise PermissionDenied("Your account isn't linked to a company yet.")
        serializer.save(company=comp, created_by=self.request.user)

    def perform_update(self, serializer):
        comp = _user_company(self.request)
        if comp is None:
            raise PermissionDenied("Your account isn't linked to a company yet.")
        serializer.save(company=comp)


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = productSerializer

    def get_queryset(self):
        comp = _user_company(self.request)
        if comp is None:
            return product.objects.none()
        return product.objects.filter(company=comp).prefetch_related('stocks')

    def create(self, request, *args, **kwargs):
        comp = _user_company(request)
        if comp is None:
            raise PermissionDenied("Your account isn't linked to a company yet.")

        warehouse_id = request.data.get('warehouse')
        initial_qty = request.data.get('initial_quantity', 0)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product_obj = serializer.save(company=comp)

        if warehouse_id:
            try:
                warehouse_obj = warehouse.objects.get(id=warehouse_id, company=comp)
                try:
                    qty = int(initial_qty)
                except (TypeError, ValueError):
                    qty = 0
                warehouse_stock.objects.create(
                    product=product_obj, warehouse=warehouse_obj, quantity=qty,
                )
            except warehouse.DoesNotExist:
                pass

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_update(self, serializer):
        comp = _user_company(self.request)
        if comp is None:
            raise PermissionDenied("Your account isn't linked to a company yet.")
        serializer.save(company=comp)


class WarehouseStockViewSet(viewsets.ModelViewSet):
    serializer_class = warehouseStockSerializer

    def get_queryset(self):
        comp = _user_company(self.request)
        if comp is None:
            return warehouse_stock.objects.none()
        qs = warehouse_stock.objects.select_related('warehouse', 'product').filter(
            warehouse__company=comp
        )
        warehouse_id = self.request.query_params.get('warehouse')
        if warehouse_id:
            qs = qs.filter(warehouse_id=warehouse_id)
        return qs


class SellableProductViewSet(viewsets.ModelViewSet):
    serializer_class = SellableProductSerializer

    def get_queryset(self):
        comp = _user_company(self.request)
        if comp is None:
            return SellableProduct.objects.none()
        return SellableProduct.objects.filter(company=comp).prefetch_related(
            'recipe_items__ingredient'
        )

    def _check_ingredients_belong_to_company(self, comp):
        """Every recipe ingredient must be a product in the user's company."""
        items = self.request.data.get('recipe_items', []) or []
        for it in items:
            ing_id = it.get('ingredient')
            if ing_id is None:
                continue
            if not product.objects.filter(id=ing_id, company=comp).exists():
                raise PermissionDenied("One of the ingredients isn't a product in your company.")

    def perform_create(self, serializer):
        comp = _user_company(self.request)
        if comp is None:
            raise PermissionDenied("Your account isn't linked to a company yet.")
        self._check_ingredients_belong_to_company(comp)
        serializer.save(company=comp)

    def perform_update(self, serializer):
        comp = _user_company(self.request)
        if comp is None:
            raise PermissionDenied("Your account isn't linked to a company yet.")
        self._check_ingredients_belong_to_company(comp)
        serializer.save(company=comp)

    @action(detail=True, methods=['post'])
    def produce(self, request, pk=None):
        """Produce a batch of this finished product.
        Body: { "warehouse": <id>, "quantity": <batch size> }
        - needed[ingredient] = recipe.quantity * batch
        - blocks if ANY ingredient is short (nothing deducted)
        - deducts each ingredient (stock_out), adds finished goods (stock_in)
        - all atomic
        """
        comp = _user_company(request)
        if comp is None:
            raise PermissionDenied("Your account isn't linked to a company yet.")

        sellable = self.get_object()  # already company-scoped by get_queryset

        wh_id = request.data.get('warehouse')
        try:
            batch = Decimal(str(request.data.get('quantity')))
        except (TypeError, ValueError, ArithmeticError):
            raise ValidationError("Quantity must be a number.")
        if batch <= 0:
            raise ValidationError("Quantity must be greater than zero.")

        try:
            wh = warehouse.objects.get(id=wh_id, company=comp)
        except warehouse.DoesNotExist:
            raise ValidationError("Pick a valid warehouse in your company.")

        recipe = list(sellable.recipe_items.select_related('ingredient').all())
        if not recipe:
            raise ValidationError("This product has no recipe, so nothing can be produced.")

        with db_transaction.atomic():
            # 1) check every ingredient has enough, lock the rows
            shortages = []
            stock_rows = {}
            for item in recipe:
                needed = Decimal(item.quantity) * batch
                stock = warehouse_stock.objects.select_for_update().filter(
                    warehouse=wh, product=item.ingredient
                ).first()
                have = Decimal(stock.quantity) if stock else Decimal('0')
                if needed > have:
                    shortages.append(
                        f"{item.ingredient.name}: need {needed} {item.ingredient.unit}, have {have}"
                    )
                stock_rows[item.ingredient.id] = (stock, needed)

            if shortages:
                raise ValidationError({
                    "detail": "Not enough stock to produce this batch.",
                    "shortages": shortages,
                })

            # 2) deduct ingredients + log stock_out
            for item in recipe:
                stock, needed = stock_rows[item.ingredient.id]
                stock.quantity = Decimal(stock.quantity) - needed
                stock.save()
                InventoryTransaction.objects.create(
                    warehouse=wh, product=item.ingredient, quantity=needed,
                    transaction_type='stock_out',
                    note=f"Produced {batch} x {sellable.name}",
                    created_by=request.user,
                )

            # 3) add finished goods to stock + log stock_in
            fp = sellable.finished_product
            if fp is not None:
                fstock, _ = warehouse_stock.objects.select_for_update().get_or_create(
                    warehouse=wh, product=fp, defaults={'quantity': 0}
                )
                fstock.quantity = Decimal(fstock.quantity) + batch
                fstock.save()
                InventoryTransaction.objects.create(
                    warehouse=wh, product=fp, quantity=batch,
                    transaction_type='stock_in',
                    note=f"Produced batch of {sellable.name}",
                    created_by=request.user,
                )

        return Response({
            "produced": float(batch),
            "product": sellable.name,
            "warehouse": wh.name,
            "message": f"Produced {batch} x {sellable.name}. Ingredients deducted from {wh.name}.",
        }, status=status.HTTP_200_OK)


class InventoryTransactionViewSet(viewsets.ModelViewSet):
    """Records a stock movement AND applies it to warehouse_stock atomically.
      stock_in   -> stock += quantity
      stock_out  -> stock -= quantity   (blocked if not enough)
      adjustment -> stock  = quantity
    """
    serializer_class = InventoryTransactionSerializer

    def get_queryset(self):
        comp = _user_company(self.request)
        if comp is None:
            return InventoryTransaction.objects.none()
        qs = InventoryTransaction.objects.select_related('warehouse', 'product', 'created_by').filter(
            warehouse__company=comp
        )
        wid = self.request.query_params.get('warehouse')
        if wid:
            qs = qs.filter(warehouse_id=wid)
        return qs

    def create(self, request, *args, **kwargs):
        comp = _user_company(request)
        if comp is None:
            raise PermissionDenied("Your account isn't linked to a company yet.")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        wh = serializer.validated_data['warehouse']
        prod = serializer.validated_data['product']
        qty = Decimal(serializer.validated_data['quantity'])
        ttype = serializer.validated_data['transaction_type']

        # both warehouse and product must belong to the user's company
        if wh.company_id != comp.id or prod.company_id != comp.id:
            raise PermissionDenied("Warehouse and product must belong to your company.")

        # everything (stock update + log row) succeeds or fails together
        with db_transaction.atomic():
            stock, _ = warehouse_stock.objects.select_for_update().get_or_create(
                warehouse=wh, product=prod, defaults={'quantity': 0}
            )
            current = Decimal(stock.quantity)

            if ttype == 'stock_in':
                stock.quantity = current + qty
            elif ttype == 'stock_out':
                if qty > current:
                    raise ValidationError(
                        f"Not enough stock. {prod.name} @ {wh.name} has {current} {prod.unit}, "
                        f"but you tried to remove {qty}."
                    )
                stock.quantity = current - qty
            elif ttype == 'adjustment':
                stock.quantity = qty
            stock.save()

            txn = serializer.save(created_by=request.user)

        out = self.get_serializer(txn)
        headers = self.get_success_headers(out.data)
        return Response(out.data, status=status.HTTP_201_CREATED, headers=headers)


class StockOrderViewSet(viewsets.ModelViewSet):
    """Incoming/outgoing orders with a status lifecycle. Stock only moves
    when an order becomes 'delivered', and reverses if a delivered order
    is cancelled. All transitions are atomic and logged as transactions."""
    serializer_class = StockOrderSerializer

    def get_queryset(self):
        comp = _user_company(self.request)
        if comp is None:
            return StockOrder.objects.none()
        qs = StockOrder.objects.select_related('warehouse', 'product', 'created_by').filter(company=comp)
        direction = self.request.query_params.get('direction')
        if direction:
            qs = qs.filter(direction=direction)
        return qs

    def perform_create(self, serializer):
        comp = _user_company(self.request)
        if comp is None:
            raise PermissionDenied("Your account isn't linked to a company yet.")
        wh = serializer.validated_data['warehouse']
        prod = serializer.validated_data['product']
        if wh.company_id != comp.id or prod.company_id != comp.id:
            raise PermissionDenied("Warehouse and product must belong to your company.")
        # new orders always start pending, stock not yet applied
        serializer.save(company=comp, created_by=self.request.user,
                        status='pending', stock_applied=False)

    def _apply_stock(self, order, request):
        """Apply the order's stock change (called when -> delivered).
        incoming: +qty, outgoing: -qty (blocked if short). Logs a transaction."""
        qty = Decimal(order.quantity)
        with db_transaction.atomic():
            stock, _ = warehouse_stock.objects.select_for_update().get_or_create(
                warehouse=order.warehouse, product=order.product, defaults={'quantity': 0}
            )
            current = Decimal(stock.quantity)
            if order.direction == 'incoming':
                stock.quantity = current + qty
                ttype = 'stock_in'
            else:  # outgoing
                if qty > current:
                    raise ValidationError(
                        f"Not enough stock to deliver. {order.product.name} @ "
                        f"{order.warehouse.name} has {current} {order.product.unit}, "
                        f"but the order is for {qty}."
                    )
                stock.quantity = current - qty
                ttype = 'stock_out'
            stock.save()
            InventoryTransaction.objects.create(
                warehouse=order.warehouse, product=order.product, quantity=qty,
                transaction_type=ttype,
                note=f"Order #{order.id} delivered ({order.direction})",
                created_by=request.user,
            )
            order.stock_applied = True
            order.status = 'delivered'
            order.save()

    def _reverse_stock(self, order, request):
        """Undo a delivered order's stock change (called when delivered -> cancelled).
        Reverses direction; blocked if it would make stock negative."""
        qty = Decimal(order.quantity)
        with db_transaction.atomic():
            stock, _ = warehouse_stock.objects.select_for_update().get_or_create(
                warehouse=order.warehouse, product=order.product, defaults={'quantity': 0}
            )
            current = Decimal(stock.quantity)
            if order.direction == 'incoming':
                # undo an addition -> subtract; block if already used
                if qty > current:
                    raise ValidationError(
                        f"Can't cancel: the received stock has already been used. "
                        f"{order.product.name} @ {order.warehouse.name} has {current}, "
                        f"need {qty} to reverse."
                    )
                stock.quantity = current - qty
                ttype = 'stock_out'
            else:
                # undo a removal -> add back
                stock.quantity = current + qty
                ttype = 'stock_in'
            stock.save()
            InventoryTransaction.objects.create(
                warehouse=order.warehouse, product=order.product, quantity=qty,
                transaction_type=ttype,
                note=f"Order #{order.id} cancelled after delivery — reversed",
                created_by=request.user,
            )
            order.stock_applied = False
            order.status = 'cancelled'
            order.save()

    @action(detail=True, methods=['post'])
    def set_status(self, request, pk=None):
        """Move an order to a new status. Body: { "status": "in_transit" }
        Applies/reverses stock on the delivered boundary."""
        comp = _user_company(request)
        if comp is None:
            raise PermissionDenied("Your account isn't linked to a company yet.")
        order = self.get_object()
        new_status = request.data.get('status')
        valid = dict(StockOrder.STATUS_CHOICES)
        if new_status not in valid:
            raise ValidationError("Invalid status.")

        old_status = order.status
        if new_status == old_status:
            return Response(self.get_serializer(order).data)

        # transitions that move stock:
        if new_status == 'delivered' and not order.stock_applied:
            self._apply_stock(order, request)          # apply + set delivered
        elif old_status == 'delivered' and order.stock_applied and new_status == 'cancelled':
            self._reverse_stock(order, request)         # reverse + set cancelled
        else:
            # plain status change (pending/in_transit/cancelled-without-delivery)
            order.status = new_status
            order.save()

        return Response(self.get_serializer(order).data)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def default_sales_warehouse(request):
    """GET returns the company's default sales warehouse; POST sets it.
    Body for POST: { "warehouse": <id> }"""
    comp = _user_company(request)
    if comp is None:
        raise PermissionDenied("Your account isn't linked to a company yet.")
    if request.method == 'POST':
        wh_id = request.data.get('warehouse')
        if wh_id in (None, ''):
            comp.default_sales_warehouse = None
        else:
            try:
                wh = warehouse.objects.get(id=wh_id, company=comp)
            except warehouse.DoesNotExist:
                raise ValidationError("Pick a valid warehouse in your company.")
            comp.default_sales_warehouse = wh
        comp.save()
    return Response({
        "warehouse": comp.default_sales_warehouse_id,
        "warehouse_name": comp.default_sales_warehouse.name if comp.default_sales_warehouse else None,
    })


class SaleViewSet(viewsets.ModelViewSet):
    """Record a sale: a basket of sellable items. For each line, if the item
    has a recipe, deduct its ingredients (qty x recipe) from the sale warehouse.
    All-or-nothing: if ANY recipe item is short, nothing is recorded. Items with
    no recipe are still saved as untracked lines (no stock change)."""
    serializer_class = SaleSerializer

    def get_queryset(self):
        comp = _user_company(self.request)
        if comp is None:
            return Sale.objects.none()
        return Sale.objects.filter(company=comp).prefetch_related('items__sellable', 'warehouse')

    def create(self, request, *args, **kwargs):
        comp = _user_company(request)
        if comp is None:
            raise PermissionDenied("Your account isn't linked to a company yet.")

        # resolve warehouse: explicit in body, else company default
        wh_id = request.data.get('warehouse') or comp.default_sales_warehouse_id
        if not wh_id:
            raise ValidationError("No sales warehouse set. Pick one or set a default in Settings.")
        try:
            wh = warehouse.objects.get(id=wh_id, company=comp)
        except warehouse.DoesNotExist:
            raise ValidationError("Pick a valid warehouse in your company.")

        items = request.data.get('items', []) or []
        if not items:
            raise ValidationError("Add at least one item to the sale.")

        # load sellables (company-scoped) with recipes
        sellable_ids = [it.get('sellable') for it in items]
        sellables = {s.id: s for s in SellableProduct.objects.filter(
            id__in=sellable_ids, company=comp).prefetch_related('recipe_items__ingredient')}

        # build required ingredient totals across the whole basket
        # needed[ingredient_id] = total qty required from this warehouse
        needed = {}
        parsed = []  # (sellable, qty, has_recipe)
        for it in items:
            sid = it.get('sellable')
            s = sellables.get(sid)
            if s is None:
                raise ValidationError("One of the items isn't a sellable product in your company.")
            try:
                qty = Decimal(str(it.get('quantity')))
            except (TypeError, ValueError, ArithmeticError):
                raise ValidationError(f"Bad quantity for {s.name}.")
            if qty <= 0:
                raise ValidationError(f"Quantity for {s.name} must be greater than zero.")
            recipe = list(s.recipe_items.all())
            for ri in recipe:
                needed[ri.ingredient_id] = needed.get(ri.ingredient_id, Decimal('0')) + Decimal(ri.quantity) * qty
            parsed.append((s, qty, bool(recipe)))

        with db_transaction.atomic():
            # 1) check ALL ingredients across the basket, lock rows
            shortages = []
            locked = {}
            for ing_id, need in needed.items():
                stock = warehouse_stock.objects.select_for_update().filter(
                    warehouse=wh, product_id=ing_id).first()
                have = Decimal(stock.quantity) if stock else Decimal('0')
                if need > have:
                    ing = product.objects.get(id=ing_id)
                    shortages.append(f"{ing.name}: need {need} {ing.unit}, have {have}")
                locked[ing_id] = stock
            if shortages:
                raise ValidationError({
                    "detail": "Not enough stock to record this sale.",
                    "shortages": shortages,
                })

            # 2) deduct ingredients + log transactions
            for ing_id, need in needed.items():
                stock = locked[ing_id]
                stock.quantity = Decimal(stock.quantity) - need
                stock.save()
                InventoryTransaction.objects.create(
                    warehouse=wh, product_id=ing_id, quantity=need,
                    transaction_type='stock_out', note="Sale",
                    created_by=request.user,
                )

            # 3) create the sale + line items
            total = Decimal('0')
            sale = Sale.objects.create(company=comp, warehouse=wh,
                                       note=request.data.get('note') or None,
                                       created_by=request.user)
            for s, qty, has_recipe in parsed:
                price = s.selling_price
                if price is not None:
                    total += Decimal(price) * qty
                SaleItem.objects.create(
                    sale=sale, sellable=s, quantity=qty,
                    unit_price=price, tracked=has_recipe,
                )
            sale.total_price = total
            sale.save()

        out = self.get_serializer(sale)
        return Response(out.data, status=status.HTTP_201_CREATED)


# ---------------- Template (HTML page) views ----------------
class LoginTemplateView(TemplateView):
    template_name = 'login.html'

class DashboardTemplateView(TemplateView):
    template_name = 'index.html'

class WarehouseTemplateView(TemplateView):
    template_name = 'warehouses.html'

class WarehouseDetailTemplateView(TemplateView):
    template_name = 'warehouse_detail.html'

class ProductTemplateView(TemplateView):
    template_name = 'products.html'

class StockTemplateView(TemplateView):
    template_name = 'stock.html'

class SellableTemplateView(TemplateView):
    template_name = 'sellable.html'

class TransactionsTemplateView(TemplateView):
    template_name = 'transactions.html'

class OrdersTemplateView(TemplateView):
    template_name = 'orders.html'

class SalesTemplateView(TemplateView):
    template_name = 'sales.html'