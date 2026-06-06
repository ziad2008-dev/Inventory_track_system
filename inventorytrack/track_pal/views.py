from django.shortcuts import render
from .models import company, SellableProduct, RecipeItem, warehouse, product, warehouse_stock, InventoryTransaction
from .serializers import SellableProductSerializer, warehouseSerializer, productSerializer, warehouseStockSerializer, InventoryTransactionSerializer
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.decorators import api_view, permission_classes
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