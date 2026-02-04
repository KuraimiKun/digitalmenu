"""Analytics views."""
from rest_framework import viewsets, generics, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count, Avg, F
from django.db.models.functions import TruncDate, TruncHour
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404

from apps.restaurants.models import Restaurant
from apps.orders.models import Order, OrderItem
from apps.menus.models import MenuItem, Category
from .models import (
    DailySalesReport, MenuItemAnalytics, CategoryAnalytics,
    CustomerAnalytics, HourlySalesData, PopularItemsReport
)
from .serializers import (
    DailySalesReportSerializer, MenuItemAnalyticsSerializer,
    CategoryAnalyticsSerializer, CustomerAnalyticsSerializer,
    HourlySalesDataSerializer, PopularItemsReportSerializer,
    DashboardSummarySerializer, DateRangeSerializer
)


class AnalyticsDashboardView(generics.GenericAPIView):
    """Main analytics dashboard endpoint."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, restaurant_slug):
        """Get dashboard summary data."""
        restaurant = get_object_or_404(Restaurant, slug=restaurant_slug)
        
        # Default to last 30 days
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        # Get date range from query params
        period = request.query_params.get('period', '30d')
        if period == '7d':
            start_date = end_date - timedelta(days=7)
        elif period == '90d':
            start_date = end_date - timedelta(days=90)
        elif period == '1y':
            start_date = end_date - timedelta(days=365)
        
        # Previous period for comparison
        period_length = (end_date - start_date).days
        prev_end_date = start_date - timedelta(days=1)
        prev_start_date = prev_end_date - timedelta(days=period_length)
        
        # Current period stats
        current_orders = Order.objects.filter(
            restaurant=restaurant,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            status__in=[Order.Status.COMPLETED, Order.Status.DELIVERED, Order.Status.PICKED_UP]
        )
        
        current_stats = current_orders.aggregate(
            total_revenue=Sum('total'),
            total_orders=Count('id'),
            avg_order_value=Avg('total')
        )
        
        # Previous period stats
        prev_orders = Order.objects.filter(
            restaurant=restaurant,
            created_at__date__gte=prev_start_date,
            created_at__date__lte=prev_end_date,
            status__in=[Order.Status.COMPLETED, Order.Status.DELIVERED, Order.Status.PICKED_UP]
        )
        
        prev_stats = prev_orders.aggregate(
            total_revenue=Sum('total'),
            total_orders=Count('id')
        )
        
        # Calculate changes
        current_revenue = current_stats['total_revenue'] or 0
        prev_revenue = prev_stats['total_revenue'] or 1  # Avoid division by zero
        revenue_change = ((current_revenue - prev_revenue) / prev_revenue) * 100 if prev_revenue else 0
        
        current_order_count = current_stats['total_orders'] or 0
        prev_order_count = prev_stats['total_orders'] or 1
        orders_change = ((current_order_count - prev_order_count) / prev_order_count) * 100 if prev_order_count else 0
        
        # Customer stats
        total_customers = current_orders.values('customer').distinct().count()
        new_customers = current_orders.filter(
            customer__date_joined__gte=start_date
        ).values('customer').distinct().count()
        
        # Top items
        top_items = OrderItem.objects.filter(
            order__restaurant=restaurant,
            order__created_at__date__gte=start_date,
            order__created_at__date__lte=end_date
        ).values('menu_item__name', 'menu_item_id').annotate(
            quantity=Sum('quantity'),
            revenue=Sum(F('unit_price') * F('quantity'))
        ).order_by('-quantity')[:10]
        
        # Order types breakdown
        order_types = current_orders.values('order_type').annotate(
            count=Count('id')
        )
        order_types_dict = {ot['order_type']: ot['count'] for ot in order_types}
        
        # Peak hours
        hourly_data = current_orders.annotate(
            hour=TruncHour('created_at')
        ).values('hour').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        return Response({
            'period': period,
            'date_range': {
                'start': start_date,
                'end': end_date
            },
            'total_revenue': current_revenue,
            'revenue_change': round(revenue_change, 2),
            'total_orders': current_order_count,
            'orders_change': round(orders_change, 2),
            'average_order_value': current_stats['avg_order_value'] or 0,
            'total_customers': total_customers,
            'new_customers': new_customers,
            'top_items': list(top_items),
            'order_types': order_types_dict,
            'peak_hours': list(hourly_data)
        })


class DailySalesReportViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for daily sales reports."""
    serializer_class = DailySalesReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        restaurant_slug = self.kwargs.get('restaurant_slug')
        queryset = DailySalesReport.objects.filter(restaurant__slug=restaurant_slug)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        location_id = self.request.query_params.get('location_id')
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        if location_id:
            queryset = queryset.filter(location_id=location_id)
        
        return queryset


class MenuItemAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for menu item analytics."""
    serializer_class = MenuItemAnalyticsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        restaurant_slug = self.kwargs.get('restaurant_slug')
        queryset = MenuItemAnalytics.objects.filter(restaurant__slug=restaurant_slug)
        
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def top_sellers(self, request, restaurant_slug=None):
        """Get top selling items."""
        days = int(request.query_params.get('days', 30))
        limit = int(request.query_params.get('limit', 10))
        start_date = timezone.now().date() - timedelta(days=days)
        
        queryset = self.get_queryset().filter(date__gte=start_date)
        
        top_items = queryset.values(
            'menu_item', 'menu_item__name', 'menu_item__image'
        ).annotate(
            total_quantity=Sum('quantity_sold'),
            total_revenue=Sum('revenue'),
            total_views=Sum('views')
        ).order_by('-total_quantity')[:limit]
        
        return Response(list(top_items))


class CustomerAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for customer analytics."""
    serializer_class = CustomerAnalyticsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        restaurant_slug = self.kwargs.get('restaurant_slug')
        return CustomerAnalytics.objects.filter(restaurant__slug=restaurant_slug)
    
    @action(detail=False, methods=['get'])
    def top_customers(self, request, restaurant_slug=None):
        """Get top customers by spending."""
        limit = int(request.query_params.get('limit', 20))
        
        top_customers = self.get_queryset().order_by('-total_spent')[:limit]
        serializer = CustomerAnalyticsSerializer(top_customers, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def at_risk(self, request, restaurant_slug=None):
        """Get customers at risk of churning."""
        days_threshold = int(request.query_params.get('days', 30))
        
        at_risk = self.get_queryset().filter(
            days_since_last_order__gte=days_threshold,
            total_orders__gte=2
        ).order_by('-total_spent')[:50]
        
        serializer = CustomerAnalyticsSerializer(at_risk, many=True)
        return Response(serializer.data)


class RevenueChartView(generics.GenericAPIView):
    """Get revenue data for charts."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, restaurant_slug):
        restaurant = get_object_or_404(Restaurant, slug=restaurant_slug)
        
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        daily_revenue = DailySalesReport.objects.filter(
            restaurant=restaurant,
            date__gte=start_date,
            date__lte=end_date
        ).values('date').annotate(
            revenue=Sum('gross_revenue'),
            orders=Sum('total_orders')
        ).order_by('date')
        
        return Response(list(daily_revenue))


class OrdersChartView(generics.GenericAPIView):
    """Get order data for charts."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, restaurant_slug):
        restaurant = get_object_or_404(Restaurant, slug=restaurant_slug)
        
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Orders by day
        daily_orders = Order.objects.filter(
            restaurant=restaurant,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            total=Count('id'),
            completed=Count('id', filter=F('status').in_([
                Order.Status.COMPLETED,
                Order.Status.DELIVERED,
                Order.Status.PICKED_UP
            ])),
            cancelled=Count('id', filter=F('status') == Order.Status.CANCELLED)
        ).order_by('date')
        
        return Response(list(daily_orders))


class PeakHoursView(generics.GenericAPIView):
    """Get peak hours data."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, restaurant_slug):
        restaurant = get_object_or_404(Restaurant, slug=restaurant_slug)
        
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timedelta(days=days)
        
        hourly_data = HourlySalesData.objects.filter(
            restaurant=restaurant,
            date__gte=start_date
        ).values('hour').annotate(
            avg_orders=Avg('order_count'),
            avg_revenue=Avg('revenue')
        ).order_by('hour')
        
        return Response(list(hourly_data))


class TrackEventView(generics.CreateAPIView):
    """Track analytics events (menu views, etc.)."""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, restaurant_slug):
        """Track an analytics event."""
        from .models import MenuViewEvent
        
        restaurant = get_object_or_404(Restaurant, slug=restaurant_slug)
        
        event = MenuViewEvent.objects.create(
            restaurant=restaurant,
            menu_id=request.data.get('menu_id'),
            menu_item_id=request.data.get('menu_item_id'),
            session_id=request.session.session_key or 'anonymous',
            user=request.user if request.user.is_authenticated else None,
            event_type=request.data.get('event_type', 'view'),
            device_type=request.data.get('device_type', ''),
            browser=request.data.get('browser', ''),
            referrer=request.data.get('referrer', ''),
            ip_address=self.get_client_ip(request)
        )
        
        return Response({'tracked': True}, status=status.HTTP_201_CREATED)
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')
