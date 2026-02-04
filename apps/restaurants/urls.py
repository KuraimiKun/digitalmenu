"""Restaurant URL patterns."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from .views import (
    RestaurantViewSet,
    LocationViewSet,
    OperatingHoursViewSet,
    SpecialHoursViewSet,
    TableViewSet,
    PublicRestaurantView,
    PublicLocationView,
)

# Main router
router = DefaultRouter()
router.register(r'', RestaurantViewSet, basename='restaurant')

# Nested router for locations
restaurant_router = routers.NestedDefaultRouter(router, r'', lookup='restaurant')
restaurant_router.register(r'locations', LocationViewSet, basename='restaurant-locations')

# Nested router for location resources
location_router = routers.NestedDefaultRouter(restaurant_router, r'locations', lookup='location')
location_router.register(r'hours', OperatingHoursViewSet, basename='location-hours')
location_router.register(r'special-hours', SpecialHoursViewSet, basename='location-special-hours')
location_router.register(r'tables', TableViewSet, basename='location-tables')

urlpatterns = [
    # Public endpoints
    path('public/<slug:slug>/', PublicRestaurantView.as_view(), name='public-restaurant'),
    path('public/<slug:restaurant_slug>/locations/<slug:slug>/', PublicLocationView.as_view(), name='public-location'),
    
    # API routes
    path('', include(router.urls)),
    path('', include(restaurant_router.urls)),
    path('', include(location_router.urls)),
]
