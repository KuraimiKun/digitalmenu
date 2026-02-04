"""Menu URL patterns."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from .views import (
    MenuThemeViewSet,
    MenuViewSet,
    CategoryViewSet,
    MenuItemViewSet,
    MenuItemVariantViewSet,
    ModifierGroupViewSet,
    ModifierViewSet,
    PublicMenuView,
    PublicMenuListView,
)

# Main router for themes
router = DefaultRouter()
router.register(r'themes', MenuThemeViewSet, basename='menu-themes')

urlpatterns = [
    # Public endpoints
    path('public/<slug:restaurant_slug>/', PublicMenuListView.as_view(), name='public-menu-list'),
    path('public/<slug:restaurant_slug>/<slug:slug>/', PublicMenuView.as_view(), name='public-menu'),
    
    # Theme routes
    path('', include(router.urls)),
    
    # Restaurant-scoped menu routes (to be nested under restaurants)
    # These are mounted at /api/v1/restaurants/{slug}/menus/
]

# Nested routers for use with restaurant URLs
def get_menu_router(parent_router, parent_prefix, lookup):
    """Create nested router for menus under restaurants."""
    menu_router = routers.NestedDefaultRouter(parent_router, parent_prefix, lookup=lookup)
    menu_router.register(r'menus', MenuViewSet, basename='restaurant-menus')
    
    # Categories under menus
    category_router = routers.NestedDefaultRouter(menu_router, r'menus', lookup='menu')
    category_router.register(r'categories', CategoryViewSet, basename='menu-categories')
    
    # Items under categories
    item_router = routers.NestedDefaultRouter(category_router, r'categories', lookup='category')
    item_router.register(r'items', MenuItemViewSet, basename='category-items')
    
    # Variants under items
    variant_router = routers.NestedDefaultRouter(item_router, r'items', lookup='item')
    variant_router.register(r'variants', MenuItemVariantViewSet, basename='item-variants')
    
    # Modifier groups under restaurant
    modifier_router = routers.NestedDefaultRouter(parent_router, parent_prefix, lookup=lookup)
    modifier_router.register(r'modifier-groups', ModifierGroupViewSet, basename='restaurant-modifier-groups')
    
    # Modifiers under groups
    modifier_item_router = routers.NestedDefaultRouter(modifier_router, r'modifier-groups', lookup='group')
    modifier_item_router.register(r'modifiers', ModifierViewSet, basename='group-modifiers')
    
    return [menu_router, category_router, item_router, variant_router, modifier_router, modifier_item_router]
