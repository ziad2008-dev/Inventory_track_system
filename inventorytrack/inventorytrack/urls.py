from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from track_pal import views

router = DefaultRouter()
router.register(r'warehouses', views.WarehouseViewSet, basename='api-warehouse')
router.register(r'products', views.ProductViewSet, basename='api-product')
router.register(r'warehouse-stock', views.WarehouseStockViewSet, basename='api-stock')
router.register(r'sellable-products', views.SellableProductViewSet, basename='api-sellable')
router.register(r'transactions', views.InventoryTransactionViewSet, basename='api-transaction')
router.register(r'orders', views.StockOrderViewSet, basename='api-order')
router.register(r'sales', views.SaleViewSet, basename='api-sale')

urlpatterns = [
    path('admin/', admin.site.urls),

    # REST API
    path('api/', include(router.urls)),

    # JWT auth endpoints (djangorestframework-simplejwt)
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/me/', views.me, name='api-me'),

    # Frontend HTML pages
    path('', views.LoginTemplateView.as_view(), name='login-ui'),                         # login is the landing page
    path('dashboard/', views.DashboardTemplateView.as_view(), name='dashboard-ui'),
    path('warehouses/', views.WarehouseTemplateView.as_view(), name='warehouses-ui'),
    path('warehouse/<int:pk>/', views.WarehouseDetailTemplateView.as_view(), name='warehouse-detail-ui'),
    path('products-ui/', views.ProductTemplateView.as_view(), name='products-ui'),
    path('stock-ui/', views.StockTemplateView.as_view(), name='stock-ui'),
    path('sellable-ui/', views.SellableTemplateView.as_view(), name='sellable-ui'),
    path('transactions-ui/', views.TransactionsTemplateView.as_view(), name='transactions-ui'),
    path('orders-ui/', views.OrdersTemplateView.as_view(), name='orders-ui'),
    path('sales-ui/', views.SalesTemplateView.as_view(), name='sales-ui'),
    path('export-ui/', views.ExportTemplateView.as_view(), name='export-ui'),
    path('api/default-sales-warehouse/', views.default_sales_warehouse, name='default-sales-warehouse'),
]