"""
Digital Menu SaaS - Main URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from apps.core.health import health_check, health_check_detailed

urlpatterns = [
    # Health checks (for load balancers and monitoring)
    path('health/', health_check, name='health-check'),
    path('health/detailed/', health_check_detailed, name='health-check-detailed'),
    
    # Admin
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # API v1 endpoints
    path('api/v1/auth/', include('apps.core.urls.auth_urls')),
    path('api/v1/users/', include('apps.core.urls.user_urls')),
    path('api/v1/restaurants/', include('apps.restaurants.urls')),
    path('api/v1/menus/', include('apps.menus.urls')),
    path('api/v1/orders/', include('apps.orders.urls')),
    path('api/v1/analytics/', include('apps.analytics.urls')),
    path('api/v1/promotions/', include('apps.promotions.urls')),
    path('api/v1/integrations/', include('apps.integrations.urls')),
    path('api/v1/qrcodes/', include('apps.qrcodes.urls')),
    
    # Frontend views
    path('', include('apps.core.urls.frontend_urls')),
    
    # Allauth
    path('accounts/', include('allauth.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Debug toolbar
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass
