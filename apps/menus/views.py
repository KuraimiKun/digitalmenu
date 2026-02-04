"""Menu views with drag-and-drop builder support."""
from rest_framework import viewsets, generics, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db import transaction

from apps.core.permissions import HasRestaurantAccess, CanManageMenu
from apps.restaurants.models import Restaurant
from .models import (
    Menu, Category, MenuItem, MenuItemVariant,
    ModifierGroup, Modifier, MenuItemModifierGroup,
    MenuTheme
)
from .serializers import (
    MenuSerializer, MenuListSerializer, MenuCreateSerializer,
    MenuBuilderSerializer, MenuReorderSerializer, MenuPublishSerializer,
    CategorySerializer, CategoryListSerializer,
    MenuItemSerializer, MenuItemListSerializer,
    MenuItemVariantSerializer, ModifierGroupSerializer,
    ModifierSerializer, MenuItemModifierGroupSerializer,
    MenuThemeSerializer, MenuItemBulkUpdateSerializer,
    CategoryReorderSerializer
)


class MenuThemeViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for menu themes."""
    queryset = MenuTheme.objects.filter(is_active=True)
    serializer_class = MenuThemeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        qs = super().get_queryset()
        # Filter premium themes based on subscription
        if not self.request.user.is_staff:
            # TODO: Check user's subscription for premium themes
            pass
        return qs


class MenuViewSet(viewsets.ModelViewSet):
    """ViewSet for managing menus."""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'menu_type', 'is_active']
    lookup_field = 'slug'
    
    def get_queryset(self):
        restaurant_slug = self.kwargs.get('restaurant_slug')
        return Menu.objects.filter(restaurant__slug=restaurant_slug)
    
    def get_serializer_class(self):
        if self.action == 'list':
            return MenuListSerializer
        if self.action == 'create':
            return MenuCreateSerializer
        if self.action == 'builder':
            return MenuBuilderSerializer
        return MenuSerializer
    
    def perform_create(self, serializer):
        restaurant_slug = self.kwargs.get('restaurant_slug')
        restaurant = get_object_or_404(Restaurant, slug=restaurant_slug)
        serializer.save(restaurant=restaurant, created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def builder(self, request, restaurant_slug=None, slug=None):
        """Get full menu data for the builder interface."""
        menu = self.get_object()
        serializer = MenuBuilderSerializer(menu)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def publish(self, request, restaurant_slug=None, slug=None):
        """Publish a menu to specified locations."""
        menu = self.get_object()
        serializer = MenuPublishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        menu.status = Menu.Status.PUBLISHED
        if serializer.validated_data.get('locations'):
            menu.locations.set(serializer.validated_data['locations'])
        menu.save()
        
        return Response({
            'detail': 'Menu published successfully.',
            'menu': MenuSerializer(menu).data
        })
    
    @action(detail=True, methods=['post'])
    def unpublish(self, request, restaurant_slug=None, slug=None):
        """Unpublish a menu (set to draft)."""
        menu = self.get_object()
        menu.status = Menu.Status.DRAFT
        menu.save()
        return Response({'detail': 'Menu unpublished.'})
    
    @action(detail=True, methods=['post'])
    def duplicate(self, request, restaurant_slug=None, slug=None):
        """Duplicate a menu with all its contents."""
        original_menu = self.get_object()
        
        with transaction.atomic():
            # Clone menu
            new_menu = Menu.objects.get(pk=original_menu.pk)
            new_menu.pk = None
            new_menu.id = None
            new_menu.name = f"{original_menu.name} (Copy)"
            new_menu.slug = None
            new_menu.status = Menu.Status.DRAFT
            new_menu.save()
            
            # Clone categories and items
            for category in original_menu.categories.all():
                original_category_pk = category.pk
                category.pk = None
                category.id = None
                category.menu = new_menu
                category.slug = None
                category.save()
                
                # Clone items in category
                for item in MenuItem.objects.filter(category_id=original_category_pk):
                    item.pk = None
                    item.id = None
                    item.category = category
                    item.slug = None
                    item.save()
        
        return Response({
            'detail': 'Menu duplicated successfully.',
            'menu': MenuSerializer(new_menu).data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def reorder_categories(self, request, restaurant_slug=None, slug=None):
        """Reorder categories within a menu (drag-and-drop)."""
        menu = self.get_object()
        serializer = CategoryReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            for cat_data in serializer.validated_data['categories']:
                Category.objects.filter(
                    id=cat_data['id'],
                    menu=menu
                ).update(position=cat_data['position'])
        
        return Response({'detail': 'Categories reordered.'})
    
    @action(detail=True, methods=['get'])
    def export(self, request, restaurant_slug=None, slug=None):
        """Export menu data as JSON."""
        menu = self.get_object()
        serializer = MenuBuilderSerializer(menu)
        return Response(serializer.data)


class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing menu categories."""
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        menu_slug = self.kwargs.get('menu_slug')
        restaurant_slug = self.kwargs.get('restaurant_slug')
        return Category.objects.filter(
            menu__slug=menu_slug,
            menu__restaurant__slug=restaurant_slug
        )
    
    def get_serializer_class(self):
        if self.action == 'list':
            return CategoryListSerializer
        return CategorySerializer
    
    def perform_create(self, serializer):
        menu_slug = self.kwargs.get('menu_slug')
        restaurant_slug = self.kwargs.get('restaurant_slug')
        menu = get_object_or_404(
            Menu,
            slug=menu_slug,
            restaurant__slug=restaurant_slug
        )
        serializer.save(menu=menu)
    
    @action(detail=True, methods=['post'])
    def reorder_items(self, request, restaurant_slug=None, menu_slug=None, pk=None):
        """Reorder items within a category (drag-and-drop)."""
        category = self.get_object()
        serializer = MenuReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            for item_data in serializer.validated_data['items']:
                MenuItem.objects.filter(
                    id=item_data['id'],
                    category=category
                ).update(position=item_data['position'])
        
        return Response({'detail': 'Items reordered.'})
    
    @action(detail=True, methods=['post'])
    def move_item(self, request, restaurant_slug=None, menu_slug=None, pk=None):
        """Move an item to a different category."""
        target_category = self.get_object()
        item_id = request.data.get('item_id')
        position = request.data.get('position', 0)
        
        item = get_object_or_404(MenuItem, id=item_id)
        item.category = target_category
        item.position = position
        item.save()
        
        return Response({'detail': 'Item moved successfully.'})


class MenuItemViewSet(viewsets.ModelViewSet):
    """ViewSet for managing menu items."""
    serializer_class = MenuItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'is_featured', 'is_vegetarian', 'is_vegan']
    
    def get_queryset(self):
        category_pk = self.kwargs.get('category_pk')
        return MenuItem.objects.filter(category_id=category_pk)
    
    def get_serializer_class(self):
        if self.action == 'list':
            return MenuItemListSerializer
        return MenuItemSerializer
    
    def perform_create(self, serializer):
        category_pk = self.kwargs.get('category_pk')
        category = get_object_or_404(Category, pk=category_pk)
        serializer.save(category=category)
    
    @action(detail=False, methods=['post'])
    def bulk_update(self, request, category_pk=None):
        """Bulk update menu items."""
        serializer = MenuItemBulkUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        item_ids = serializer.validated_data['item_ids']
        action_type = serializer.validated_data['action']
        
        items = MenuItem.objects.filter(id__in=item_ids, category_id=category_pk)
        
        with transaction.atomic():
            if action_type == 'activate':
                items.update(status=MenuItem.Status.AVAILABLE)
            elif action_type == 'deactivate':
                items.update(status=MenuItem.Status.HIDDEN)
            elif action_type == 'feature':
                items.update(is_featured=True)
            elif action_type == 'unfeature':
                items.update(is_featured=False)
            elif action_type == 'mark_available':
                items.update(status=MenuItem.Status.AVAILABLE)
            elif action_type == 'mark_out_of_stock':
                items.update(status=MenuItem.Status.OUT_OF_STOCK)
            elif action_type == 'delete':
                items.delete()
        
        return Response({'detail': f'Bulk {action_type} completed.'})
    
    @action(detail=True, methods=['post'])
    def update_availability(self, request, category_pk=None, pk=None):
        """Quick update item availability (real-time stock)."""
        item = self.get_object()
        is_available = request.data.get('is_available', True)
        
        if is_available:
            item.status = MenuItem.Status.AVAILABLE
        else:
            item.status = MenuItem.Status.OUT_OF_STOCK
        item.save()
        
        return Response({'detail': 'Availability updated.', 'status': item.status})


class MenuItemVariantViewSet(viewsets.ModelViewSet):
    """ViewSet for managing menu item variants."""
    serializer_class = MenuItemVariantSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        item_pk = self.kwargs.get('item_pk')
        return MenuItemVariant.objects.filter(item_id=item_pk)
    
    def perform_create(self, serializer):
        item_pk = self.kwargs.get('item_pk')
        item = get_object_or_404(MenuItem, pk=item_pk)
        serializer.save(item=item)


class ModifierGroupViewSet(viewsets.ModelViewSet):
    """ViewSet for managing modifier groups."""
    serializer_class = ModifierGroupSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        restaurant_slug = self.kwargs.get('restaurant_slug')
        return ModifierGroup.objects.filter(restaurant__slug=restaurant_slug)
    
    def perform_create(self, serializer):
        restaurant_slug = self.kwargs.get('restaurant_slug')
        restaurant = get_object_or_404(Restaurant, slug=restaurant_slug)
        serializer.save(restaurant=restaurant)


class ModifierViewSet(viewsets.ModelViewSet):
    """ViewSet for managing modifiers."""
    serializer_class = ModifierSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        group_pk = self.kwargs.get('group_pk')
        return Modifier.objects.filter(group_id=group_pk)
    
    def perform_create(self, serializer):
        group_pk = self.kwargs.get('group_pk')
        group = get_object_or_404(ModifierGroup, pk=group_pk)
        serializer.save(group=group)


class PublicMenuView(generics.RetrieveAPIView):
    """Public menu view (no auth required)."""
    serializer_class = MenuBuilderSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'
    
    def get_queryset(self):
        restaurant_slug = self.kwargs.get('restaurant_slug')
        return Menu.objects.filter(
            restaurant__slug=restaurant_slug,
            status=Menu.Status.PUBLISHED,
            is_active=True
        )


class PublicMenuListView(generics.ListAPIView):
    """Public list of menus for a restaurant."""
    serializer_class = MenuListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        restaurant_slug = self.kwargs.get('restaurant_slug')
        return Menu.objects.filter(
            restaurant__slug=restaurant_slug,
            status=Menu.Status.PUBLISHED,
            is_active=True
        )
