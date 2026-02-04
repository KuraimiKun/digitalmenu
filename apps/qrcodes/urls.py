"""QR Codes URL patterns."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
    # Public scan endpoint
    path('scan/<str:short_code>/', views.scan_qr_code, name='scan-qr-code'),
    path('info/<str:short_code>/', views.get_qr_info, name='qr-code-info'),
]

# These URLs are registered under restaurants app
restaurant_qr_patterns = [
    # QR Code Designs
    path(
        '<uuid:restaurant_pk>/qr-designs/',
        views.QRCodeDesignViewSet.as_view({
            'get': 'list',
            'post': 'create'
        }),
        name='qr-designs'
    ),
    path(
        '<uuid:restaurant_pk>/qr-designs/<uuid:pk>/',
        views.QRCodeDesignViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy'
        }),
        name='qr-design-detail'
    ),
    path(
        '<uuid:restaurant_pk>/qr-designs/<uuid:pk>/set-default/',
        views.QRCodeDesignViewSet.as_view({'post': 'set_default'}),
        name='qr-design-set-default'
    ),
    
    # QR Codes
    path(
        '<uuid:restaurant_pk>/qr-codes/',
        views.QRCodeViewSet.as_view({
            'get': 'list',
            'post': 'create'
        }),
        name='qr-codes'
    ),
    path(
        '<uuid:restaurant_pk>/qr-codes/by-location/',
        views.QRCodeViewSet.as_view({'get': 'by_location'}),
        name='qr-codes-by-location'
    ),
    path(
        '<uuid:restaurant_pk>/qr-codes/<uuid:pk>/',
        views.QRCodeViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy'
        }),
        name='qr-code-detail'
    ),
    path(
        '<uuid:restaurant_pk>/qr-codes/<uuid:pk>/regenerate/',
        views.QRCodeViewSet.as_view({'post': 'regenerate'}),
        name='qr-code-regenerate'
    ),
    path(
        '<uuid:restaurant_pk>/qr-codes/<uuid:pk>/analytics/',
        views.QRCodeViewSet.as_view({'get': 'analytics'}),
        name='qr-code-analytics'
    ),
    path(
        '<uuid:restaurant_pk>/qr-codes/<uuid:pk>/scans/',
        views.QRCodeViewSet.as_view({'get': 'scans'}),
        name='qr-code-scans'
    ),
    
    # QR Code Batches
    path(
        '<uuid:restaurant_pk>/qr-batches/',
        views.QRCodeBatchViewSet.as_view({
            'get': 'list',
            'post': 'create'
        }),
        name='qr-batches'
    ),
    path(
        '<uuid:restaurant_pk>/qr-batches/<uuid:pk>/',
        views.QRCodeBatchViewSet.as_view({
            'get': 'retrieve',
            'delete': 'destroy'
        }),
        name='qr-batch-detail'
    ),
    path(
        '<uuid:restaurant_pk>/qr-batches/<uuid:pk>/qr-codes/',
        views.QRCodeBatchViewSet.as_view({'get': 'qr_codes'}),
        name='qr-batch-codes'
    ),
]
