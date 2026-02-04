"""Custom permissions for role-based access control."""
from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """Only allow platform admins."""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class IsRestaurantOwner(permissions.BasePermission):
    """Allow restaurant owners."""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['admin', 'owner']


class IsRestaurantManager(permissions.BasePermission):
    """Allow restaurant managers and above."""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['admin', 'owner', 'manager']


class IsRestaurantStaff(permissions.BasePermission):
    """Allow restaurant staff and above."""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['admin', 'owner', 'manager', 'staff']


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Allow write access only to owners."""
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Check if user owns the object
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        
        return False


class HasRestaurantAccess(permissions.BasePermission):
    """Check if user has access to the restaurant."""
    
    def has_object_permission(self, request, view, obj):
        from apps.restaurants.models import RestaurantStaff
        
        # Get restaurant from object
        restaurant = None
        if hasattr(obj, 'restaurant'):
            restaurant = obj.restaurant
        elif hasattr(obj, 'location') and hasattr(obj.location, 'restaurant'):
            restaurant = obj.location.restaurant
        elif hasattr(obj, 'menu') and hasattr(obj.menu, 'restaurant'):
            restaurant = obj.menu.restaurant
        
        if not restaurant:
            return False
        
        # Check if user is staff at this restaurant
        return RestaurantStaff.objects.filter(
            user=request.user,
            restaurant=restaurant,
            is_active=True
        ).exists()


class CanManageMenu(permissions.BasePermission):
    """Check if user can manage menus (manager+)."""
    
    def has_object_permission(self, request, view, obj):
        from apps.restaurants.models import RestaurantStaff
        
        restaurant = getattr(obj, 'restaurant', None)
        if not restaurant:
            return False
        
        return RestaurantStaff.objects.filter(
            user=request.user,
            restaurant=restaurant,
            role__in=['owner', 'manager'],
            is_active=True
        ).exists()
