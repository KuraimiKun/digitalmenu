"""Analytics admin configuration."""
from django.contrib import admin
from .models import (
    DailySalesReport, MenuItemAnalytics, CategoryAnalytics,
    CustomerAnalytics, MenuViewEvent, HourlySalesData, PopularItemsReport
)


@admin.register(DailySalesReport)
class DailySalesReportAdmin(admin.ModelAdmin):
    list_display = [
        'restaurant', 'location', 'date', 'total_orders',
        'gross_revenue', 'net_revenue'
    ]
    list_filter = ['restaurant', 'date']
    date_hierarchy = 'date'


@admin.register(MenuItemAnalytics)
class MenuItemAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['menu_item', 'date', 'quantity_sold', 'revenue', 'views']
    list_filter = ['restaurant', 'date']
    search_fields = ['menu_item__name']


@admin.register(CustomerAnalytics)
class CustomerAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'customer', 'restaurant', 'total_orders', 'total_spent',
        'loyalty_tier', 'last_order_date'
    ]
    list_filter = ['restaurant', 'loyalty_tier']
    search_fields = ['customer__email']


@admin.register(MenuViewEvent)
class MenuViewEventAdmin(admin.ModelAdmin):
    list_display = ['restaurant', 'event_type', 'session_id', 'device_type', 'created_at']
    list_filter = ['event_type', 'device_type', 'restaurant']
    readonly_fields = ['created_at']
