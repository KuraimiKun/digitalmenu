"""Order views."""
from rest_framework import viewsets, generics, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
import uuid

from apps.restaurants.models import Restaurant, Location, Table
from apps.menus.models import MenuItem, MenuItemVariant
from .models import Order, OrderItem, OrderStatusHistory, Cart, CartItem, Review
from .serializers import (
    OrderSerializer, OrderListSerializer, OrderCreateSerializer,
    OrderUpdateStatusSerializer, OrderItemSerializer,
    CartSerializer, CartItemSerializer, AddToCartSerializer,
    UpdateCartItemSerializer, ApplyPromoCodeSerializer,
    ReviewSerializer, ReviewResponseSerializer
)


class OrderViewSet(viewsets.ModelViewSet):
    """ViewSet for managing orders."""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'order_type', 'payment_status']
    
    def get_queryset(self):
        user = self.request.user
        restaurant_slug = self.kwargs.get('restaurant_slug')
        
        if restaurant_slug:
            return Order.objects.filter(restaurant__slug=restaurant_slug)
        
        # Return user's orders if customer
        if user.role == 'customer':
            return Order.objects.filter(customer=user)
        
        # Return orders for restaurants user has access to
        from apps.restaurants.models import RestaurantStaff
        restaurant_ids = RestaurantStaff.objects.filter(
            user=user, is_active=True
        ).values_list('restaurant_id', flat=True)
        
        return Order.objects.filter(restaurant_id__in=restaurant_ids)
    
    def get_serializer_class(self):
        if self.action == 'list':
            return OrderListSerializer
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a new order."""
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        location = get_object_or_404(Location, id=data['location_id'])
        restaurant = location.restaurant
        
        # Create order
        order = Order.objects.create(
            restaurant=restaurant,
            location=location,
            customer=request.user if request.user.is_authenticated else None,
            customer_name=data.get('customer_name', ''),
            customer_email=data.get('customer_email', ''),
            customer_phone=data.get('customer_phone', ''),
            order_type=data['order_type'],
            delivery_address=data.get('delivery_address', ''),
            delivery_instructions=data.get('delivery_instructions', ''),
            scheduled_time=data.get('scheduled_time'),
            notes=data.get('notes', ''),
            currency=location.currency,
        )
        
        # Handle table for dine-in
        if data.get('table_id'):
            table = get_object_or_404(Table, id=data['table_id'], location=location)
            order.table = table
            table.status = Table.Status.OCCUPIED
            table.save()
        
        # Add items from cart or directly
        if data.get('cart_id'):
            cart = get_object_or_404(Cart, id=data['cart_id'])
            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    menu_item=cart_item.menu_item,
                    variant=cart_item.variant,
                    name=cart_item.menu_item.name,
                    quantity=cart_item.quantity,
                    unit_price=cart_item.unit_price,
                    modifiers=cart_item.modifiers,
                    modifier_total=cart_item.modifier_total,
                    special_instructions=cart_item.special_instructions
                )
            # Clear cart
            cart.delete()
        elif data.get('items'):
            for item_data in data['items']:
                menu_item = get_object_or_404(MenuItem, id=item_data['menu_item_id'])
                variant = None
                if item_data.get('variant_id'):
                    variant = get_object_or_404(MenuItemVariant, id=item_data['variant_id'])
                
                unit_price = menu_item.price
                if variant:
                    unit_price += variant.price_adjustment
                
                OrderItem.objects.create(
                    order=order,
                    menu_item=menu_item,
                    variant=variant,
                    name=menu_item.name,
                    quantity=item_data.get('quantity', 1),
                    unit_price=unit_price,
                    modifiers=item_data.get('modifiers', []),
                    special_instructions=item_data.get('special_instructions', '')
                )
        
        # Recalculate totals
        order.calculate_totals()
        order.save()
        
        return Response(
            OrderSerializer(order).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None, **kwargs):
        """Update order status."""
        order = self.get_object()
        serializer = OrderUpdateStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        old_status = order.status
        order.status = serializer.validated_data['status']
        
        if serializer.validated_data.get('estimated_ready_time'):
            order.estimated_ready_time = serializer.validated_data['estimated_ready_time']
        
        # Set completion time
        if order.status in [Order.Status.COMPLETED, Order.Status.PICKED_UP, Order.Status.DELIVERED]:
            order.completed_at = timezone.now()
        
        if order.status == Order.Status.READY:
            order.actual_ready_time = timezone.now()
        
        order.save()
        
        # Create status history
        OrderStatusHistory.objects.create(
            order=order,
            status=order.status,
            changed_by=request.user,
            notes=serializer.validated_data.get('notes', '')
        )
        
        return Response(OrderSerializer(order).data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None, **kwargs):
        """Cancel an order."""
        order = self.get_object()
        
        if order.status in [Order.Status.COMPLETED, Order.Status.DELIVERED, Order.Status.PICKED_UP]:
            return Response(
                {'error': 'Cannot cancel completed orders'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = Order.Status.CANCELLED
        order.save()
        
        # Free up table if dine-in
        if order.table:
            order.table.status = Table.Status.AVAILABLE
            order.table.save()
        
        return Response({'detail': 'Order cancelled.'})
    
    @action(detail=False, methods=['get'])
    def active(self, request, **kwargs):
        """Get active orders (for kitchen display)."""
        queryset = self.get_queryset().filter(
            status__in=[
                Order.Status.PENDING,
                Order.Status.CONFIRMED,
                Order.Status.PREPARING,
                Order.Status.READY
            ]
        ).order_by('created_at')
        
        serializer = OrderListSerializer(queryset, many=True)
        return Response(serializer.data)


class CartViewSet(viewsets.ModelViewSet):
    """ViewSet for managing shopping carts."""
    serializer_class = CartSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Cart.objects.filter(customer=self.request.user)
        
        session_id = self.request.session.session_key
        if session_id:
            return Cart.objects.filter(session_id=session_id)
        return Cart.objects.none()
    
    def get_or_create_cart(self, restaurant_id):
        """Get or create a cart for the current session/user."""
        user = self.request.user if self.request.user.is_authenticated else None
        session_id = self.request.session.session_key
        
        if not session_id:
            self.request.session.create()
            session_id = self.request.session.session_key
        
        cart, created = Cart.objects.get_or_create(
            session_id=session_id,
            restaurant_id=restaurant_id,
            defaults={
                'customer': user,
                'expires_at': timezone.now() + timedelta(hours=24)
            }
        )
        
        return cart
    
    @action(detail=False, methods=['post'])
    def add_item(self, request):
        """Add item to cart."""
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        menu_item = get_object_or_404(MenuItem, id=data['menu_item_id'])
        
        cart = self.get_or_create_cart(menu_item.category.menu.restaurant_id)
        
        # Check for variant
        variant = None
        if data.get('variant_id'):
            variant = get_object_or_404(MenuItemVariant, id=data['variant_id'], item=menu_item)
        
        # Check if item already in cart
        existing_item = CartItem.objects.filter(
            cart=cart,
            menu_item=menu_item,
            variant=variant
        ).first()
        
        if existing_item:
            existing_item.quantity += data['quantity']
            existing_item.modifiers = data.get('modifiers', [])
            existing_item.special_instructions = data.get('special_instructions', '')
            existing_item.save()
        else:
            CartItem.objects.create(
                cart=cart,
                menu_item=menu_item,
                variant=variant,
                quantity=data['quantity'],
                modifiers=data.get('modifiers', []),
                special_instructions=data.get('special_instructions', '')
            )
        
        return Response(CartSerializer(cart).data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['patch'])
    def update_item(self, request, pk=None):
        """Update cart item quantity/modifiers."""
        cart = self.get_object()
        item_id = request.data.get('item_id')
        
        serializer = UpdateCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        
        if serializer.validated_data['quantity'] == 0:
            cart_item.delete()
        else:
            cart_item.quantity = serializer.validated_data['quantity']
            if 'modifiers' in serializer.validated_data:
                cart_item.modifiers = serializer.validated_data['modifiers']
            if 'special_instructions' in serializer.validated_data:
                cart_item.special_instructions = serializer.validated_data['special_instructions']
            cart_item.save()
        
        return Response(CartSerializer(cart).data)
    
    @action(detail=True, methods=['post'])
    def apply_promo(self, request, pk=None):
        """Apply promo code to cart."""
        cart = self.get_object()
        serializer = ApplyPromoCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # TODO: Validate promo code and calculate discount
        cart.promo_code = serializer.validated_data['promo_code']
        cart.save()
        
        return Response(CartSerializer(cart).data)
    
    @action(detail=True, methods=['post'])
    def clear(self, request, pk=None):
        """Clear all items from cart."""
        cart = self.get_object()
        cart.items.all().delete()
        return Response({'detail': 'Cart cleared.'})


class ReviewViewSet(viewsets.ModelViewSet):
    """ViewSet for managing reviews."""
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        restaurant_slug = self.kwargs.get('restaurant_slug')
        if restaurant_slug:
            return Review.objects.filter(
                order__restaurant__slug=restaurant_slug,
                is_public=True
            )
        return Review.objects.filter(customer=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)
    
    @action(detail=True, methods=['post'])
    def respond(self, request, pk=None):
        """Restaurant response to review."""
        review = self.get_object()
        serializer = ReviewResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        review.response = serializer.validated_data['response']
        review.responded_by = request.user
        review.responded_at = timezone.now()
        review.save()
        
        return Response(ReviewSerializer(review).data)


class PublicOrderCreateView(generics.CreateAPIView):
    """Public view for creating orders from the public menu (no authentication required)."""
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        """Create a new order from public menu."""
        from apps.restaurants.models import Restaurant, Location, Table
        from apps.menus.models import MenuItem
        
        # Get restaurant from URL
        restaurant_slug = kwargs.get('restaurant_slug')
        restaurant = get_object_or_404(Restaurant, slug=restaurant_slug)
        
        # Check if ordering is enabled
        if not restaurant.ordering_enabled:
            return Response(
                {'detail': 'Online ordering is not available for this restaurant.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = request.data
        
        # Get or find location
        location_id = data.get('location_id')
        if location_id:
            location = get_object_or_404(Location, id=location_id, restaurant=restaurant)
        else:
            # Use primary location or first location
            location = Location.objects.filter(restaurant=restaurant, is_primary=True).first()
            if not location:
                location = Location.objects.filter(restaurant=restaurant).first()
            if not location:
                return Response(
                    {'detail': 'No location available for orders.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Validate order type
        order_type = data.get('order_type', 'dine_in')
        if order_type not in ['dine_in', 'pickup', 'delivery']:
            order_type = 'dine_in'
        
        # Get table if provided (for dine-in orders)
        table = None
        table_id = data.get('table_id')
        if table_id and order_type == 'dine_in':
            try:
                table = Table.objects.get(id=table_id)
            except (Table.DoesNotExist, ValueError):
                pass  # Table not found, proceed without it
        
        # Create order
        order = Order.objects.create(
            restaurant=restaurant,
            location=location,
            customer=request.user if request.user.is_authenticated else None,
            customer_name=data.get('customer_name', ''),
            customer_email=data.get('customer_email', ''),
            customer_phone=data.get('customer_phone', ''),
            order_type=order_type,
            table=table,
            delivery_address=data.get('delivery_address', ''),
            notes=data.get('notes', ''),
            currency=restaurant.default_currency,
        )
        
        # Add items
        items = data.get('items', [])
        if not items:
            order.delete()
            return Response(
                {'detail': 'Order must have at least one item.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        for item_data in items:
            menu_item_id = item_data.get('menu_item_id')
            if not menu_item_id:
                continue
                
            try:
                menu_item = MenuItem.objects.get(id=menu_item_id)
            except MenuItem.DoesNotExist:
                continue
            
            quantity = item_data.get('quantity', 1)
            if quantity < 1:
                quantity = 1
            
            OrderItem.objects.create(
                order=order,
                menu_item=menu_item,
                name=menu_item.name,
                quantity=quantity,
                unit_price=menu_item.price,
                special_instructions=item_data.get('special_instructions', '')
            )
        
        # Check if any items were added
        if order.items.count() == 0:
            order.delete()
            return Response(
                {'detail': 'No valid items in the order.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate totals
        order.calculate_totals()
        order.save()
        
        # Create status history
        OrderStatusHistory.objects.create(
            order=order,
            status=order.status,
            notes='Order placed from public menu'
        )
        
        return Response({
            'id': str(order.id),
            'order_number': order.order_number,
            'status': order.status,
            'total': str(order.total),
            'message': 'Order placed successfully!'
        }, status=status.HTTP_201_CREATED)


class PublicOrderTrackingView(generics.RetrieveAPIView):
    """Public view for tracking orders by order number."""
    serializer_class = OrderSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'order_number'
    
    def get_queryset(self):
        return Order.objects.all()
