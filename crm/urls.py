from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import exports, drivers_views, orders as orders_views, clients as clients_views, containers as containers_views, api as api_views, drivers_admin, loyalty, notifications_views, telegram_integration

router = DefaultRouter()
router.register(r'clients', views.ClientViewSet)
router.register(r'orders', views.OrderViewSet)
router.register(r'containers', views.ContainerViewSet)
router.register(r'drivers', views.DriverViewSet)
router.register(r'regions', views.RegionViewSet)

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('orders/', orders_views.orders, name='orders'),
    path('create-order/', orders_views.create_order, name='create_order'),
    path('edit-order/', orders_views.edit_order, name='edit_order'),
    path('delete-order/<int:order_id>/', orders_views.delete_order, name='delete_order'),
    path('drivers/', drivers_admin.drivers, name='drivers'),
    path('create-driver/', drivers_admin.create_driver, name='create_driver'),
    path('edit-driver/', drivers_admin.edit_driver, name='edit_driver'),
    path('delete-driver/<int:driver_id>/', drivers_admin.delete_driver, name='delete_driver'),
    path('regions/', views.regions, name='regions'),
    path('create-region/', views.create_region, name='create_region'),
    path('edit-region/', views.edit_region, name='edit_region'),
    path('delete-region/<int:region_id>/', views.delete_region, name='delete_region'),
    path('clients/', clients_views.clients, name='clients'),
    path('create-client/', clients_views.create_client, name='create_client'),
    path('edit-client/', clients_views.edit_client, name='edit_client'),
    path('delete-client/<int:client_id>/', clients_views.delete_client, name='delete_client'),
    path('containers/', containers_views.containers, name='containers'),
    path('create-container/', containers_views.create_container, name='create_container'),
    path('edit-container/', containers_views.edit_container, name='edit_container'),
    path('return-container/<int:container_id>/', containers_views.return_container, name='return_container'),
    path('bulk-return-containers/', containers_views.bulk_return_containers, name='bulk_return_containers'),    path('delete-container/<int:container_id>/', containers_views.delete_container, name='delete_container'),
    path('export-orders-by-day-csv/', exports.export_orders_by_day_csv, name='export_orders_by_day_csv'),
    path('export-revenue-by-month-csv/', exports.export_revenue_by_month_csv, name='export_revenue_by_month_csv'),
    path('create-product/', views.create_product, name='create_product'),
    path('driver-dashboard/', drivers_views.driver_dashboard, name='driver_dashboard'),
    path('routes/', views.routes, name='routes'),
    path('reports/', views.reports, name='reports'),
    path('export-orders-xlsx/', exports.export_orders_xlsx, name='export_orders_xlsx'),
    path('export-containers-xlsx/', exports.export_containers_xlsx, name='export_containers_xlsx'),
    path('create-route/', views.create_route, name='create_route'),
    path('route/<int:route_id>/', views.route_detail, name='route_detail'),
    path('api/', include(router.urls)),
    path('api/orders/<int:order_id>/update/', api_views.api_update_order, name='api_update_order'),
    path('notifications/', notifications_views.notifications_list, name='notifications_list'),
    path('notifications/<int:notification_id>/mark-read/', notifications_views.mark_notification_read, name='mark_notification_read'),
    path('loyalty/', loyalty.loyalty_dashboard, name='loyalty_dashboard'),
    path('loyalty/program/new/', loyalty.loyalty_program_edit, name='loyalty_program_new'),
    path('loyalty/program/<int:program_id>/', loyalty.loyalty_program_edit, name='loyalty_program_edit'),
    path('loyalty/category/new/', loyalty.loyalty_category_edit, name='loyalty_category_new'),
    path('loyalty/category/<int:category_id>/', loyalty.loyalty_category_edit, name='loyalty_category_edit'),
    path('loyalty/transactions/', loyalty.loyalty_transactions, name='loyalty_transactions'),
    path('attach-client-to-region/', views.attach_client_to_region, name='attach_client_to_region'),
    path('driver/update-order/<int:order_id>/', drivers_views.driver_update_order, name='driver_update_order'),
    # Telegram bot integration
    path('approve-client/<int:client_id>/', telegram_integration.approve_client_registration, name='approve_client'),
    path('reject-client/<int:client_id>/', telegram_integration.reject_client_registration, name='reject_client'),
    path('generate-driver-code/<int:driver_id>/', telegram_integration.generate_driver_access_code, name='generate_driver_code_web'),
]