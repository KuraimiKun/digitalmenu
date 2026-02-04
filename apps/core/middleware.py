"""Tenant middleware for multi-tenant support."""
from django.utils.deprecation import MiddlewareMixin


class TenantMiddleware(MiddlewareMixin):
    """
    Middleware to handle multi-tenant context.
    Sets the current restaurant/tenant context based on subdomain or header.
    """
    
    def process_request(self, request):
        # Get tenant from subdomain or header
        host = request.get_host().split(':')[0]
        subdomain = host.split('.')[0] if '.' in host else None
        
        # Also check for explicit header
        tenant_header = request.META.get('HTTP_X_TENANT_ID')
        
        # Store tenant info in request for later use
        request.tenant_subdomain = subdomain
        request.tenant_id = tenant_header
        
        return None
