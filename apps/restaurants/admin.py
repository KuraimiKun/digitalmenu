"""Restaurant admin configuration."""
from django.contrib import admin
from .models import Restaurant, Location, OperatingHours, SpecialHours, RestaurantStaff, Table


class LocationInline(admin.TabularInline):
    model = Location
    extra = 0
    fields = ['name', 'city', 'status', 'is_primary']


class RestaurantStaffInline(admin.TabularInline):
    model = RestaurantStaff
    extra = 0
    fields = ['user', 'role', 'is_active']
    raw_id_fields = ['user']


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'owner', 'status', 'is_featured', 'created_at']
    list_filter = ['status', 'is_featured', 'created_at']
    search_fields = ['name', 'slug', 'owner__email']
    prepopulated_fields = {'slug': ('name',)}
    raw_id_fields = ['owner', 'subscription']
    inlines = [LocationInline, RestaurantStaffInline]


class OperatingHoursInline(admin.TabularInline):
    model = OperatingHours
    extra = 0


class TableInline(admin.TabularInline):
    model = Table
    extra = 0


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'restaurant', 'city', 'status', 'is_primary']
    list_filter = ['status', 'is_primary', 'restaurant']
    search_fields = ['name', 'city', 'restaurant__name']
    inlines = [OperatingHoursInline, TableInline]


@admin.register(RestaurantStaff)
class RestaurantStaffAdmin(admin.ModelAdmin):
    list_display = ['user', 'restaurant', 'role', 'is_active', 'invited_at']
    list_filter = ['role', 'is_active', 'restaurant']
    search_fields = ['user__email', 'restaurant__name']
    raw_id_fields = ['user', 'restaurant']
