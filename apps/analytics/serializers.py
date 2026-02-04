"""Analytics serializers."""
from rest_framework import serializers
from .models import (
    DailySalesReport, MenuItemAnalytics, CategoryAnalytics,
    CustomerAnalytics, HourlySalesData, PopularItemsReport
)


class DailySalesReportSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(source='location.name', read_only=True)
    
    class Meta:
        model = DailySalesReport
        fields = [
            'id', 'date', 'location', 'location_name',
            'total_orders', 'completed_orders', 'cancelled_orders',
            'dine_in_orders', 'takeout_orders', 'delivery_orders',
            'gross_revenue', 'net_revenue', 'tax_collected',
            'discounts_given', 'tips_received', 'delivery_fees',
            'average_order_value', 'average_items_per_order',
            'total_items_sold', 'unique_customers',
            'new_customers', 'returning_customers'
        ]


class MenuItemAnalyticsSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='menu_item.name', read_only=True)
    conversion_rate = serializers.FloatField(read_only=True)
    
    class Meta:
        model = MenuItemAnalytics
        fields = [
            'id', 'menu_item', 'item_name', 'date',
            'quantity_sold', 'revenue', 'views', 'add_to_cart',
            'conversion_rate'
        ]


class CategoryAnalyticsSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = CategoryAnalytics
        fields = [
            'id', 'category', 'category_name', 'date',
            'items_sold', 'revenue', 'views'
        ]


class CustomerAnalyticsSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    customer_email = serializers.EmailField(source='customer.email', read_only=True)
    
    class Meta:
        model = CustomerAnalytics
        fields = [
            'id', 'customer', 'customer_name', 'customer_email',
            'total_orders', 'total_spent', 'average_order_value',
            'favorite_items', 'favorite_categories', 'preferred_order_type',
            'last_order_date', 'days_since_last_order',
            'loyalty_points', 'loyalty_tier'
        ]


class HourlySalesDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = HourlySalesData
        fields = ['date', 'hour', 'order_count', 'revenue', 'items_sold']


class PopularItemsReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = PopularItemsReport
        fields = [
            'id', 'period', 'start_date', 'end_date',
            'top_items', 'top_categories'
        ]


class DashboardSummarySerializer(serializers.Serializer):
    """Summary data for analytics dashboard."""
    period = serializers.CharField()
    
    # Revenue
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    revenue_change = serializers.FloatField()  # Percentage change
    
    # Orders
    total_orders = serializers.IntegerField()
    orders_change = serializers.FloatField()
    average_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    # Customers
    total_customers = serializers.IntegerField()
    new_customers = serializers.IntegerField()
    
    # Top performers
    top_items = serializers.ListField()
    top_categories = serializers.ListField()
    
    # Order breakdown
    order_types = serializers.DictField()
    
    # Peak hours
    peak_hours = serializers.ListField()


class DateRangeSerializer(serializers.Serializer):
    """Serializer for date range queries."""
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    location_id = serializers.UUIDField(required=False, allow_null=True)
    
    def validate(self, attrs):
        if attrs['start_date'] > attrs['end_date']:
            raise serializers.ValidationError("Start date must be before end date")
        return attrs
