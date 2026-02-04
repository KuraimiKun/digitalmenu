"""QR Code views."""
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Count
from django.db.models.functions import TruncDate, ExtractHour
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.core.permissions import IsRestaurantOwner, IsRestaurantManager
from .models import QRCodeDesign, QRCode, QRCodeScan, QRCodeBatch
from .serializers import (
    QRCodeDesignSerializer, QRCodeSerializer, QRCodeScanSerializer,
    QRCodeBatchSerializer, QRCodeAnalyticsSerializer, PublicQRCodeSerializer
)


class QRCodeDesignViewSet(viewsets.ModelViewSet):
    """ViewSet for managing QR code designs."""
    
    serializer_class = QRCodeDesignSerializer
    permission_classes = [IsAuthenticated, IsRestaurantOwner | IsRestaurantManager]
    
    def get_queryset(self):
        return QRCodeDesign.objects.filter(
            restaurant_id=self.kwargs['restaurant_pk']
        )
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        from apps.restaurants.models import Restaurant
        context['restaurant'] = get_object_or_404(
            Restaurant, pk=self.kwargs['restaurant_pk']
        )
        return context
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, restaurant_pk=None, pk=None):
        """Set this design as the default."""
        design = self.get_object()
        design.is_default = True
        design.save()
        return Response({'status': 'set_as_default'})


class QRCodeViewSet(viewsets.ModelViewSet):
    """ViewSet for managing QR codes."""
    
    serializer_class = QRCodeSerializer
    permission_classes = [IsAuthenticated, IsRestaurantOwner | IsRestaurantManager]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['qr_type', 'location', 'is_active']
    search_fields = ['name', 'short_code']
    ordering_fields = ['created_at', 'scan_count', 'name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return QRCode.objects.filter(
            restaurant_id=self.kwargs['restaurant_pk']
        ).select_related('location', 'menu', 'table', 'design')
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        from apps.restaurants.models import Restaurant
        context['restaurant'] = get_object_or_404(
            Restaurant, pk=self.kwargs['restaurant_pk']
        )
        return context
    
    @action(detail=True, methods=['post'])
    def regenerate(self, request, restaurant_pk=None, pk=None):
        """Regenerate QR code image."""
        qr_code = self.get_object()
        qr_code.generate_qr_image()
        qr_code.save()
        return Response({
            'status': 'regenerated',
            'qr_image': qr_code.qr_image.url if qr_code.qr_image else None
        })
    
    @action(detail=True, methods=['get'])
    def analytics(self, request, restaurant_pk=None, pk=None):
        """Get analytics for this QR code."""
        qr_code = self.get_object()
        
        # Date range
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timezone.timedelta(days=days)
        
        scans = qr_code.scans.filter(scanned_at__gte=start_date)
        
        # Total scans
        total_scans = scans.count()
        
        # Unique devices
        unique_devices = scans.values('session_id').distinct().count()
        
        # Scans by date
        scans_by_date = list(
            scans.annotate(date=TruncDate('scanned_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )
        
        # Scans by device type
        scans_by_device = dict(
            scans.values_list('device_type')
            .annotate(count=Count('id'))
        )
        
        # Scans by country
        scans_by_country = dict(
            scans.exclude(country='')
            .values_list('country')
            .annotate(count=Count('id'))
        )
        
        # Top hours
        top_hours = list(
            scans.annotate(hour=ExtractHour('scanned_at'))
            .values('hour')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )
        
        data = {
            'total_scans': total_scans,
            'unique_devices': unique_devices,
            'scans_by_date': scans_by_date,
            'scans_by_device': scans_by_device,
            'scans_by_country': scans_by_country,
            'top_hours': top_hours,
        }
        
        serializer = QRCodeAnalyticsSerializer(data)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def scans(self, request, restaurant_pk=None, pk=None):
        """Get scan history for this QR code."""
        qr_code = self.get_object()
        scans = qr_code.scans.all()[:100]
        serializer = QRCodeScanSerializer(scans, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_location(self, request, restaurant_pk=None):
        """Get QR codes grouped by location."""
        from apps.restaurants.models import Location
        
        locations = Location.objects.filter(
            restaurant_id=restaurant_pk
        ).prefetch_related('qr_codes')
        
        data = []
        for location in locations:
            data.append({
                'location_id': location.id,
                'location_name': location.name,
                'qr_codes': QRCodeSerializer(
                    location.qr_codes.all(), many=True
                ).data
            })
        
        return Response(data)


class QRCodeBatchViewSet(viewsets.ModelViewSet):
    """ViewSet for batch QR code generation."""
    
    serializer_class = QRCodeBatchSerializer
    permission_classes = [IsAuthenticated, IsRestaurantOwner | IsRestaurantManager]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status', 'location', 'qr_type']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return QRCodeBatch.objects.filter(
            restaurant_id=self.kwargs['restaurant_pk']
        ).select_related('location', 'design', 'created_by')
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        from apps.restaurants.models import Restaurant
        context['restaurant'] = get_object_or_404(
            Restaurant, pk=self.kwargs['restaurant_pk']
        )
        return context
    
    def perform_create(self, serializer):
        batch = serializer.save()
        # Trigger async batch generation
        from .tasks import generate_qr_batch
        generate_qr_batch.delay(str(batch.id))
    
    @action(detail=True, methods=['get'])
    def qr_codes(self, request, restaurant_pk=None, pk=None):
        """Get all QR codes generated by this batch."""
        batch = self.get_object()
        qr_codes = QRCode.objects.filter(
            name__startswith=f"{batch.prefix or batch.name}"
        )
        serializer = QRCodeSerializer(qr_codes, many=True)
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def scan_qr_code(request, short_code):
    """Handle QR code scan and redirect to target."""
    try:
        qr_code = QRCode.objects.select_related('restaurant').get(
            short_code=short_code,
            is_active=True
        )
    except QRCode.DoesNotExist:
        return Response(
            {'error': 'QR code not found or inactive'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Record scan
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    # Parse user agent for device info
    device_type = 'unknown'
    if 'Mobile' in user_agent:
        device_type = 'mobile'
    elif 'Tablet' in user_agent:
        device_type = 'tablet'
    else:
        device_type = 'desktop'
    
    QRCodeScan.objects.create(
        qr_code=qr_code,
        user_agent=user_agent,
        device_type=device_type,
        ip_address=request.META.get('REMOTE_ADDR'),
        session_id=request.session.session_key or '',
        user=request.user if request.user.is_authenticated else None,
        referrer=request.META.get('HTTP_REFERER', ''),
    )
    
    # Update scan count
    qr_code.scan_count += 1
    qr_code.last_scanned_at = timezone.now()
    qr_code.save(update_fields=['scan_count', 'last_scanned_at'])
    
    # Redirect to target
    target_url = qr_code.get_target_url()
    
    # For API requests, return the URL
    if request.accepted_renderer.format == 'json':
        return Response({
            'redirect_url': target_url,
            'qr_code': PublicQRCodeSerializer(qr_code).data
        })
    
    # For browser requests, redirect
    return redirect(target_url)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_qr_info(request, short_code):
    """Get QR code info without recording a scan."""
    try:
        qr_code = QRCode.objects.select_related('restaurant', 'menu').get(
            short_code=short_code,
            is_active=True
        )
    except QRCode.DoesNotExist:
        return Response(
            {'error': 'QR code not found or inactive'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = PublicQRCodeSerializer(qr_code)
    return Response(serializer.data)
