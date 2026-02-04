"""Restaurant serializers."""
from rest_framework import serializers
from .models import Restaurant, Location, OperatingHours, SpecialHours, RestaurantStaff, Table


class OperatingHoursSerializer(serializers.ModelSerializer):
    day_name = serializers.CharField(source='get_day_of_week_display', read_only=True)
    
    class Meta:
        model = OperatingHours
        fields = [
            'id', 'day_of_week', 'day_name', 'is_closed',
            'open_time', 'close_time', 'open_time_2', 'close_time_2'
        ]


class SpecialHoursSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialHours
        fields = ['id', 'date', 'name', 'is_closed', 'open_time', 'close_time']


class TableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = [
            'id', 'number', 'name', 'capacity', 'status',
            'is_active', 'position_x', 'position_y'
        ]


class LocationSerializer(serializers.ModelSerializer):
    operating_hours = OperatingHoursSerializer(many=True, read_only=True)
    full_address = serializers.CharField(read_only=True)
    
    class Meta:
        model = Location
        fields = [
            'id', 'name', 'slug', 'address_line1', 'address_line2',
            'city', 'state', 'postal_code', 'country', 'full_address',
            'latitude', 'longitude', 'phone', 'email',
            'currency', 'language', 'timezone', 'status', 'is_primary',
            'accepts_orders', 'accepts_reservations', 'has_delivery',
            'has_pickup', 'has_dine_in', 'operating_hours', 'created_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at']


class LocationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for location lists."""
    
    class Meta:
        model = Location
        fields = ['id', 'name', 'slug', 'city', 'status', 'is_primary']


class RestaurantSerializer(serializers.ModelSerializer):
    locations = LocationListSerializer(many=True, read_only=True)
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    
    class Meta:
        model = Restaurant
        fields = [
            'id', 'name', 'slug', 'description', 'logo', 'cover_image',
            'primary_color', 'secondary_color', 'font_family',
            'email', 'phone', 'website',
            'facebook_url', 'instagram_url', 'twitter_url',
            'default_currency', 'default_language', 'timezone',
            'status', 'is_featured', 'custom_domain',
            'owner_name', 'locations', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'owner_name', 'created_at', 'updated_at']


class RestaurantListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for restaurant lists."""
    location_count = serializers.IntegerField(source='locations.count', read_only=True)
    
    class Meta:
        model = Restaurant
        fields = ['id', 'name', 'slug', 'logo', 'status', 'location_count']


class RestaurantCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating restaurants."""
    
    class Meta:
        model = Restaurant
        fields = [
            'name', 'description', 'logo', 'cover_image',
            'primary_color', 'secondary_color', 'email', 'phone',
            'default_currency', 'default_language', 'timezone'
        ]
    
    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)


class RestaurantStaffSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    location_names = serializers.SerializerMethodField()
    
    class Meta:
        model = RestaurantStaff
        fields = [
            'id', 'user', 'user_email', 'user_name', 'role',
            'locations', 'location_names', 'is_active',
            'invited_at', 'accepted_at'
        ]
        read_only_fields = ['id', 'invited_at', 'accepted_at']
    
    def get_location_names(self, obj):
        return [loc.name for loc in obj.locations.all()]


class InviteStaffSerializer(serializers.Serializer):
    """Serializer for inviting staff members."""
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=RestaurantStaff.Role.choices)
    location_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True
    )
