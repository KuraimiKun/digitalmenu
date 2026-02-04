"""Frontend views for public pages."""
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def landing_page(request):
    """Landing page for the SaaS platform."""
    return render(request, 'landing.html')


@require_GET
def public_menu(request, short_code):
    """Display public menu for customers."""
    from apps.qrcodes.models import QRCode
    from apps.restaurants.models import RestaurantTheme
    
    qr_code = get_object_or_404(
        QRCode.objects.select_related('menu', 'restaurant', 'table', 'location'),
        short_code=short_code,
        is_active=True
    )
    
    restaurant = qr_code.restaurant
    
    # Check if restaurant is active
    if not restaurant.is_active:
        return render(request, 'public/menu_unavailable.html', {
            'restaurant': restaurant,
            'reason': 'inactive',
            'message': 'This restaurant is currently not available.',
        })
    
    # Record scan
    record_scan(request, qr_code)
    
    # Get or create theme for restaurant
    try:
        theme = restaurant.theme
    except RestaurantTheme.DoesNotExist:
        # Create default theme with restaurant's colors
        theme = RestaurantTheme.objects.create(
            restaurant=restaurant,
            primary_color=restaurant.primary_color or '#E11D48',
            secondary_color=restaurant.secondary_color or '#1E293B',
        )
    
    # Get menu items
    menu = qr_code.menu
    if not menu:
        # Get first active menu for restaurant
        from apps.menus.models import Menu
        menu = Menu.objects.filter(restaurant=restaurant, is_active=True).first()
    
    categories = []
    if menu:
        from apps.menus.models import Category
        categories = Category.objects.filter(menu=menu, is_visible=True).prefetch_related('items').order_by('position')
    
    # Get table info from QR code (for dine-in)
    table = qr_code.table
    table_info = None
    if table:
        table_info = {
            'id': str(table.id),
            'number': table.number,
            'name': table.name or f"Table {table.number}",
        }
    
    context = {
        'qr_code': qr_code,
        'menu': menu,
        'restaurant': restaurant,
        'categories': categories,
        'theme': theme,
        'currency_symbol': restaurant.currency_symbol,
        'ordering_enabled': restaurant.ordering_enabled,
        'table': table,
        'table_info': table_info,
    }
    return render(request, 'public/menu.html', context)


@require_GET
def table_order(request, short_code):
    """Table ordering interface."""
    from apps.qrcodes.models import QRCode
    
    qr_code = get_object_or_404(
        QRCode.objects.select_related('table', 'restaurant', 'location'),
        short_code=short_code,
        qr_type='table',
        is_active=True
    )
    
    context = {
        'qr_code': qr_code,
        'table': qr_code.table,
        'restaurant': qr_code.restaurant,
        'location': qr_code.location,
    }
    return render(request, 'public/table_order.html', context)


@require_GET
def location_info(request, short_code):
    """Location information page."""
    from apps.qrcodes.models import QRCode
    
    qr_code = get_object_or_404(
        QRCode.objects.select_related('location', 'restaurant'),
        short_code=short_code,
        qr_type='location',
        is_active=True
    )
    
    context = {
        'qr_code': qr_code,
        'location': qr_code.location,
        'restaurant': qr_code.restaurant,
    }
    return render(request, 'public/location.html', context)


@require_GET
def leave_review(request, short_code):
    """Review submission page."""
    from apps.qrcodes.models import QRCode
    
    qr_code = get_object_or_404(
        QRCode.objects.select_related('restaurant', 'location'),
        short_code=short_code,
        qr_type='review',
        is_active=True
    )
    
    context = {
        'qr_code': qr_code,
        'restaurant': qr_code.restaurant,
        'location': qr_code.location,
    }
    return render(request, 'public/review.html', context)


@require_GET
def qr_redirect(request, short_code):
    """Generic QR code redirect."""
    from apps.qrcodes.models import QRCode
    
    qr_code = get_object_or_404(
        QRCode,
        short_code=short_code,
        is_active=True
    )
    
    return redirect(qr_code.get_target_url())


def record_scan(request, qr_code):
    """Helper to record QR code scan."""
    from apps.qrcodes.models import QRCodeScan
    from django.utils import timezone
    
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    device_type = 'mobile' if 'Mobile' in user_agent else 'desktop'
    
    QRCodeScan.objects.create(
        qr_code=qr_code,
        user_agent=user_agent,
        device_type=device_type,
        ip_address=request.META.get('REMOTE_ADDR'),
        session_id=request.session.session_key or '',
        user=request.user if request.user.is_authenticated else None,
    )
    
    qr_code.scan_count += 1
    qr_code.last_scanned_at = timezone.now()
    qr_code.save(update_fields=['scan_count', 'last_scanned_at'])
