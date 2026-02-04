"""Integration URL patterns."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Main router
router = DefaultRouter()
router.register(r'providers', views.IntegrationProviderViewSet, basename='provider')

urlpatterns = [
    path('', include(router.urls)),
    path(
        'webhooks/<uuid:integration_id>/',
        views.webhook_receiver,
        name='webhook-receiver'
    ),
]

# These URLs are registered under restaurants app
restaurant_integration_patterns = [
    # Restaurant integrations
    path(
        '<uuid:restaurant_pk>/integrations/',
        views.RestaurantIntegrationViewSet.as_view({
            'get': 'list',
            'post': 'create'
        }),
        name='restaurant-integrations'
    ),
    path(
        '<uuid:restaurant_pk>/integrations/<uuid:pk>/',
        views.RestaurantIntegrationViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy'
        }),
        name='restaurant-integration-detail'
    ),
    path(
        '<uuid:restaurant_pk>/integrations/<uuid:pk>/credentials/',
        views.RestaurantIntegrationViewSet.as_view({'post': 'credentials'}),
        name='restaurant-integration-credentials'
    ),
    path(
        '<uuid:restaurant_pk>/integrations/<uuid:pk>/connect/',
        views.RestaurantIntegrationViewSet.as_view({'post': 'connect'}),
        name='restaurant-integration-connect'
    ),
    path(
        '<uuid:restaurant_pk>/integrations/<uuid:pk>/disconnect/',
        views.RestaurantIntegrationViewSet.as_view({'post': 'disconnect'}),
        name='restaurant-integration-disconnect'
    ),
    path(
        '<uuid:restaurant_pk>/integrations/<uuid:pk>/sync/',
        views.RestaurantIntegrationViewSet.as_view({'post': 'sync'}),
        name='restaurant-integration-sync'
    ),
    path(
        '<uuid:restaurant_pk>/integrations/<uuid:pk>/logs/',
        views.RestaurantIntegrationViewSet.as_view({'get': 'logs'}),
        name='restaurant-integration-logs'
    ),
    
    # Delivery platform menus
    path(
        '<uuid:restaurant_pk>/integrations/<uuid:integration_pk>/menus/',
        views.DeliveryPlatformMenuViewSet.as_view({
            'get': 'list',
            'post': 'create'
        }),
        name='delivery-menus'
    ),
    path(
        '<uuid:restaurant_pk>/integrations/<uuid:integration_pk>/menus/<uuid:pk>/',
        views.DeliveryPlatformMenuViewSet.as_view({
            'get': 'retrieve',
            'delete': 'destroy'
        }),
        name='delivery-menu-detail'
    ),
    path(
        '<uuid:restaurant_pk>/integrations/<uuid:integration_pk>/menus/<uuid:pk>/sync/',
        views.DeliveryPlatformMenuViewSet.as_view({'post': 'sync'}),
        name='delivery-menu-sync'
    ),
    
    # Delivery orders
    path(
        '<uuid:restaurant_pk>/delivery-orders/',
        views.DeliveryOrderViewSet.as_view({'get': 'list'}),
        name='delivery-orders'
    ),
    path(
        '<uuid:restaurant_pk>/delivery-orders/<uuid:pk>/',
        views.DeliveryOrderViewSet.as_view({'get': 'retrieve'}),
        name='delivery-order-detail'
    ),
    path(
        '<uuid:restaurant_pk>/delivery-orders/<uuid:pk>/update-status/',
        views.DeliveryOrderViewSet.as_view({'post': 'update_status'}),
        name='delivery-order-update-status'
    ),
]
