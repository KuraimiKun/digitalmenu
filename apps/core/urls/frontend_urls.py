"""Frontend URL patterns."""
from django.urls import path
from django.views.generic import TemplateView
from apps.core import frontend_views, dashboard_views

urlpatterns = [
    # Public pages
    path('', TemplateView.as_view(template_name='landing/index.html'), name='home'),
    
    # Dashboard
    path('dashboard/', dashboard_views.dashboard_home, name='dashboard'),
    path('dashboard/switch-restaurant/<uuid:restaurant_id>/', dashboard_views.switch_restaurant, name='switch-restaurant'),
    path('dashboard/api/stats/', dashboard_views.api_dashboard_stats, name='api-dashboard-stats'),
    
    # Restaurant management
    path('dashboard/restaurants/', dashboard_views.restaurant_list, name='restaurant-list'),
    path('dashboard/restaurants/create/', dashboard_views.restaurant_create, name='restaurant-create'),
    path('dashboard/restaurants/<uuid:restaurant_id>/settings/', dashboard_views.restaurant_settings, name='restaurant-settings'),
    
    # Menu management
    path('dashboard/menus/', dashboard_views.menu_list, name='menu-list'),
    path('dashboard/menus/create/', dashboard_views.menu_create, name='menu-create'),
    path('dashboard/menus/<uuid:menu_id>/', dashboard_views.menu_detail, name='menu-detail'),
    path('dashboard/menus/<uuid:menu_id>/category/create/', dashboard_views.category_create, name='category-create'),
    path('dashboard/menus/<uuid:menu_id>/category/<uuid:category_id>/item/create/', dashboard_views.menu_item_create, name='menu-item-create'),
    path('dashboard/menus/<uuid:menu_id>/item/<uuid:item_id>/edit/', dashboard_views.menu_item_edit, name='menu-item-edit'),
    path('dashboard/menus/<uuid:menu_id>/item/<uuid:item_id>/delete/', dashboard_views.menu_item_delete, name='menu-item-delete'),
    
    # Order management
    path('dashboard/orders/', dashboard_views.order_list, name='order-list'),
    path('dashboard/orders/<uuid:order_id>/', dashboard_views.order_detail, name='order-detail'),
    path('dashboard/orders/<uuid:order_id>/status/', dashboard_views.order_update_status, name='order-update-status'),
    
    # QR Code management
    path('dashboard/qrcodes/', dashboard_views.qrcode_list, name='qrcode-list'),
    path('dashboard/qrcodes/create/', dashboard_views.qrcode_create, name='qrcode-create'),
    path('dashboard/qrcodes/bulk-action/', dashboard_views.qrcode_bulk_action, name='qrcode-bulk-action'),
    path('dashboard/qrcodes/<uuid:qrcode_id>/toggle/', dashboard_views.qrcode_toggle_status, name='qrcode-toggle'),
    path('dashboard/qrcodes/<uuid:qrcode_id>/delete/', dashboard_views.qrcode_delete, name='qrcode-delete'),
    path('dashboard/qrcodes/<uuid:qrcode_id>/regenerate/', dashboard_views.qrcode_regenerate, name='qrcode-regenerate'),
    
    # Location management
    path('dashboard/locations/', dashboard_views.location_list, name='location-list'),
    path('dashboard/locations/create/', dashboard_views.location_create, name='location-create'),
    
    # Table management
    path('dashboard/tables/', dashboard_views.table_list, name='table-list'),
    path('dashboard/tables/create/', dashboard_views.table_create, name='table-create'),
    path('dashboard/tables/bulk-action/', dashboard_views.table_bulk_action, name='table-bulk-action'),
    path('dashboard/tables/<uuid:table_id>/delete/', dashboard_views.table_delete, name='table-delete'),
    path('dashboard/tables/<uuid:table_id>/status/', dashboard_views.table_update_status, name='table-update-status'),
    
    # Theme customization
    path('dashboard/theme/', dashboard_views.theme_customize, name='theme-customize'),
    
    # Public QR code routes
    path('m/<str:short_code>/', frontend_views.public_menu, name='public-menu'),
    path('t/<str:short_code>/', frontend_views.table_order, name='table-order'),
    path('l/<str:short_code>/', frontend_views.location_info, name='location-info'),
    path('r/<str:short_code>/', frontend_views.leave_review, name='leave-review'),
    path('q/<str:short_code>/', frontend_views.qr_redirect, name='qr-redirect'),
]
