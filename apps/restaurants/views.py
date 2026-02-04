"""Restaurant views."""
from rest_framework import viewsets, generics, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404

from apps.core.permissions import IsRestaurantOwner, IsRestaurantManager, HasRestaurantAccess
from .models import Restaurant, Location, OperatingHours, SpecialHours, RestaurantStaff, Table
from .serializers import (
    RestaurantSerializer,
    RestaurantListSerializer,
    RestaurantCreateSerializer,
    LocationSerializer,
    LocationListSerializer,
    OperatingHoursSerializer,
    SpecialHoursSerializer,
    RestaurantStaffSerializer,
    InviteStaffSerializer,
    TableSerializer,
)


class RestaurantViewSet(viewsets.ModelViewSet):
    """ViewSet for managing restaurants."""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']
    lookup_field = 'slug'
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Restaurant.objects.all()
        
        # Get restaurants where user is staff
        restaurant_ids = RestaurantStaff.objects.filter(
            user=user,
            is_active=True
        ).values_list('restaurant_id', flat=True)
        
        return Restaurant.objects.filter(id__in=restaurant_ids)
    
    def get_serializer_class(self):
        if self.action == 'list':
            return RestaurantListSerializer
        if self.action == 'create':
            return RestaurantCreateSerializer
        return RestaurantSerializer
    
    def perform_create(self, serializer):
        restaurant = serializer.save()
        # Create staff entry for owner
        RestaurantStaff.objects.create(
            restaurant=restaurant,
            user=self.request.user,
            role=RestaurantStaff.Role.OWNER,
            is_active=True
        )
    
    @action(detail=True, methods=['get'])
    def staff(self, request, slug=None):
        """List all staff members for a restaurant."""
        restaurant = self.get_object()
        staff = RestaurantStaff.objects.filter(restaurant=restaurant)
        serializer = RestaurantStaffSerializer(staff, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def invite_staff(self, request, slug=None):
        """Invite a new staff member."""
        restaurant = self.get_object()
        serializer = InviteStaffSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # TODO: Send invitation email
        # For now, return success message
        return Response({'detail': 'Invitation sent successfully.'}, status=status.HTTP_200_OK)


class LocationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing restaurant locations."""
    serializer_class = LocationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        restaurant_slug = self.kwargs.get('restaurant_slug')
        return Location.objects.filter(restaurant__slug=restaurant_slug)
    
    def get_serializer_class(self):
        if self.action == 'list':
            return LocationListSerializer
        return LocationSerializer
    
    def perform_create(self, serializer):
        restaurant_slug = self.kwargs.get('restaurant_slug')
        restaurant = get_object_or_404(Restaurant, slug=restaurant_slug)
        serializer.save(restaurant=restaurant)


class OperatingHoursViewSet(viewsets.ModelViewSet):
    """ViewSet for managing operating hours."""
    serializer_class = OperatingHoursSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        location_id = self.kwargs.get('location_pk')
        return OperatingHours.objects.filter(location_id=location_id)
    
    def perform_create(self, serializer):
        location_id = self.kwargs.get('location_pk')
        location = get_object_or_404(Location, pk=location_id)
        serializer.save(location=location)


class SpecialHoursViewSet(viewsets.ModelViewSet):
    """ViewSet for managing special hours."""
    serializer_class = SpecialHoursSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        location_id = self.kwargs.get('location_pk')
        return SpecialHours.objects.filter(location_id=location_id)
    
    def perform_create(self, serializer):
        location_id = self.kwargs.get('location_pk')
        location = get_object_or_404(Location, pk=location_id)
        serializer.save(location=location)


class TableViewSet(viewsets.ModelViewSet):
    """ViewSet for managing tables."""
    serializer_class = TableSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        location_id = self.kwargs.get('location_pk')
        return Table.objects.filter(location_id=location_id)
    
    def perform_create(self, serializer):
        location_id = self.kwargs.get('location_pk')
        location = get_object_or_404(Location, pk=location_id)
        serializer.save(location=location)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, location_pk=None, pk=None):
        """Update table status."""
        table = self.get_object()
        new_status = request.data.get('status')
        if new_status not in dict(Table.Status.choices):
            return Response(
                {'error': 'Invalid status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        table.status = new_status
        table.save()
        return Response(TableSerializer(table).data)


class PublicRestaurantView(generics.RetrieveAPIView):
    """Public view for restaurant details (no auth required)."""
    queryset = Restaurant.objects.filter(status=Restaurant.Status.ACTIVE)
    serializer_class = RestaurantSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'


class PublicLocationView(generics.RetrieveAPIView):
    """Public view for location details."""
    serializer_class = LocationSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        restaurant_slug = self.kwargs.get('restaurant_slug')
        return Location.objects.filter(
            restaurant__slug=restaurant_slug,
            restaurant__status=Restaurant.Status.ACTIVE,
            status=Location.Status.OPEN
        )
