"""Analytics URL patterns."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AnalyticsDashboardView,
    DailySalesReportViewSet,
    MenuItemAnalyticsViewSet,
    CustomerAnalyticsViewSet,
    RevenueChartView,
    OrdersChartView,
    PeakHoursView,
    TrackEventView,
)

# These routes are nested under /api/v1/analytics/{restaurant_slug}/
urlpatterns = [
    path('<slug:restaurant_slug>/dashboard/', AnalyticsDashboardView.as_view(), name='analytics-dashboard'),
    path('<slug:restaurant_slug>/revenue/', RevenueChartView.as_view(), name='analytics-revenue'),
    path('<slug:restaurant_slug>/orders-chart/', OrdersChartView.as_view(), name='analytics-orders'),
    path('<slug:restaurant_slug>/peak-hours/', PeakHoursView.as_view(), name='analytics-peak-hours'),
    path('<slug:restaurant_slug>/track/', TrackEventView.as_view(), name='analytics-track'),
    
    # ViewSet routes (manual to handle nested restaurant_slug)
    path('<slug:restaurant_slug>/sales/', DailySalesReportViewSet.as_view({
        'get': 'list'
    }), name='analytics-sales-list'),
    path('<slug:restaurant_slug>/items/', MenuItemAnalyticsViewSet.as_view({
        'get': 'list'
    }), name='analytics-items-list'),
    path('<slug:restaurant_slug>/items/top-sellers/', MenuItemAnalyticsViewSet.as_view({
        'get': 'top_sellers'
    }), name='analytics-top-sellers'),
    path('<slug:restaurant_slug>/customers/', CustomerAnalyticsViewSet.as_view({
        'get': 'list'
    }), name='analytics-customers-list'),
    path('<slug:restaurant_slug>/customers/top/', CustomerAnalyticsViewSet.as_view({
        'get': 'top_customers'
    }), name='analytics-top-customers'),
    path('<slug:restaurant_slug>/customers/at-risk/', CustomerAnalyticsViewSet.as_view({
        'get': 'at_risk'
    }), name='analytics-at-risk-customers'),
]
