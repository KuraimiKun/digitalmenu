"""Order URL patterns."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    OrderViewSet, CartViewSet, ReviewViewSet,
    PublicOrderTrackingView, PublicOrderCreateView
)

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'carts', CartViewSet, basename='cart')
router.register(r'reviews', ReviewViewSet, basename='review')

urlpatterns = [
    path('track/<str:order_number>/', PublicOrderTrackingView.as_view(), name='order-track'),
    path('public/<str:restaurant_slug>/order/', PublicOrderCreateView.as_view(), name='public-order-create'),
    path('', include(router.urls)),
]
