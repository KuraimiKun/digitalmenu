"""Dashboard views for restaurant management."""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Avg, Q, Max
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta
from decimal import Decimal


@login_required
def dashboard_home(request):
    """Main dashboard view with overview stats."""
    from apps.restaurants.models import Restaurant, Location
    from apps.orders.models import Order
    from apps.menus.models import Menu, MenuItem
    from apps.qrcodes.models import QRCode, QRCodeScan
    
    user = request.user
    
    # Get user's restaurants
    restaurants = Restaurant.objects.filter(
        Q(owner=user) | Q(staff_members__user=user)
    ).distinct()
    
    # Get selected restaurant from session or first restaurant
    selected_restaurant_id = request.session.get('selected_restaurant_id')
    if selected_restaurant_id:
        selected_restaurant = restaurants.filter(id=selected_restaurant_id).first()
    else:
        selected_restaurant = restaurants.first()
    
    if selected_restaurant:
        request.session['selected_restaurant_id'] = str(selected_restaurant.id)
    
    # Calculate date ranges
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Initialize stats
    stats = {
        'total_orders': 0,
        'orders_today': 0,
        'orders_this_week': 0,
        'revenue_today': Decimal('0.00'),
        'revenue_this_week': Decimal('0.00'),
        'revenue_this_month': Decimal('0.00'),
        'total_menu_items': 0,
        'total_locations': 0,
        'total_qr_codes': 0,
        'qr_scans_today': 0,
        'qr_scans_this_week': 0,
        'avg_order_value': Decimal('0.00'),
        'pending_orders': 0,
    }
    
    recent_orders = []
    popular_items = []
    daily_revenue = []
    
    if selected_restaurant:
        # Order stats
        orders = Order.objects.filter(restaurant=selected_restaurant)
        stats['total_orders'] = orders.count()
        stats['orders_today'] = orders.filter(created_at__date=today).count()
        stats['orders_this_week'] = orders.filter(created_at__date__gte=week_ago).count()
        stats['pending_orders'] = orders.filter(
            status__in=['pending', 'confirmed', 'preparing']
        ).count()
        
        # Revenue stats
        completed_orders = orders.filter(status__in=['completed', 'delivered', 'picked_up'])
        revenue_today = completed_orders.filter(created_at__date=today).aggregate(
            total=Sum('total')
        )['total'] or Decimal('0.00')
        stats['revenue_today'] = revenue_today
        
        revenue_week = completed_orders.filter(created_at__date__gte=week_ago).aggregate(
            total=Sum('total')
        )['total'] or Decimal('0.00')
        stats['revenue_this_week'] = revenue_week
        
        revenue_month = completed_orders.filter(created_at__date__gte=month_ago).aggregate(
            total=Sum('total')
        )['total'] or Decimal('0.00')
        stats['revenue_this_month'] = revenue_month
        
        avg_order = completed_orders.aggregate(avg=Avg('total'))['avg']
        stats['avg_order_value'] = avg_order or Decimal('0.00')
        
        # Menu stats
        stats['total_menu_items'] = MenuItem.objects.filter(
            category__menu__restaurant=selected_restaurant, status='available'
        ).count()
        
        # Location stats
        stats['total_locations'] = Location.objects.filter(
            restaurant=selected_restaurant, status='active'
        ).count()
        
        # QR Code stats
        qr_codes = QRCode.objects.filter(restaurant=selected_restaurant)
        stats['total_qr_codes'] = qr_codes.filter(is_active=True).count()
        
        qr_scans = QRCodeScan.objects.filter(qr_code__restaurant=selected_restaurant)
        stats['qr_scans_today'] = qr_scans.filter(scanned_at__date=today).count()
        stats['qr_scans_this_week'] = qr_scans.filter(scanned_at__date__gte=week_ago).count()
        
        # Recent orders
        recent_orders = orders.select_related('customer', 'location', 'table').order_by(
            '-created_at'
        )[:10]
        
        # Popular items (last 30 days)
        from apps.orders.models import OrderItem
        popular_items = OrderItem.objects.filter(
            order__restaurant=selected_restaurant,
            order__created_at__date__gte=month_ago
        ).values(
            'menu_item__name'
        ).annotate(
            total_ordered=Sum('quantity')
        ).order_by('-total_ordered')[:5]
        
        # Daily revenue for chart (last 7 days)
        daily_revenue = completed_orders.filter(
            created_at__date__gte=week_ago
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            revenue=Sum('total'),
            orders=Count('id')
        ).order_by('date')
    
    context = {
        'restaurants': restaurants,
        'selected_restaurant': selected_restaurant,
        'stats': stats,
        'recent_orders': recent_orders,
        'popular_items': popular_items,
        'daily_revenue': list(daily_revenue),
    }
    return render(request, 'dashboard/index.html', context)


@login_required
def switch_restaurant(request, restaurant_id):
    """Switch the active restaurant in session."""
    from apps.restaurants.models import Restaurant
    
    restaurant = get_object_or_404(
        Restaurant.objects.filter(Q(owner=request.user) | Q(staff_members__user=request.user)),
        id=restaurant_id
    )
    request.session['selected_restaurant_id'] = str(restaurant.id)
    messages.success(request, f'Switched to {restaurant.name}')
    return redirect('dashboard')


@login_required
def restaurant_list(request):
    """List all restaurants for the user."""
    from apps.restaurants.models import Restaurant
    
    restaurants = Restaurant.objects.filter(
        Q(owner=request.user) | Q(staff_members__user=request.user)
    ).distinct().order_by('name')
    
    context = {
        'restaurants': restaurants,
    }
    return render(request, 'dashboard/restaurants/list.html', context)


@login_required
def restaurant_create(request):
    """Create a new restaurant."""
    from apps.restaurants.models import Restaurant
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        email = request.POST.get('email', '')
        phone = request.POST.get('phone', '')
        
        if not name:
            messages.error(request, 'Restaurant name is required.')
            return render(request, 'dashboard/restaurants/create.html')
        
        restaurant = Restaurant.objects.create(
            name=name,
            description=description,
            email=email,
            phone=phone,
            owner=request.user,
            status='active'
        )
        messages.success(request, f'Restaurant "{name}" created successfully!')
        request.session['selected_restaurant_id'] = str(restaurant.id)
        return redirect('dashboard')
    
    return render(request, 'dashboard/restaurants/create.html')


@login_required
def restaurant_settings(request, restaurant_id=None):
    """Restaurant settings page."""
    from apps.restaurants.models import Restaurant
    
    if restaurant_id:
        restaurant = get_object_or_404(
            Restaurant.objects.filter(Q(owner=request.user) | Q(staff_members__user=request.user)),
            id=restaurant_id
        )
    else:
        restaurant_id = request.session.get('selected_restaurant_id')
        if restaurant_id:
            restaurant = get_object_or_404(Restaurant, id=restaurant_id)
        else:
            messages.error(request, 'No restaurant selected.')
            return redirect('dashboard')
    
    if request.method == 'POST':
        restaurant.name = request.POST.get('name', restaurant.name)
        restaurant.description = request.POST.get('description', '')
        restaurant.email = request.POST.get('email', '')
        restaurant.phone = request.POST.get('phone', '')
        restaurant.website = request.POST.get('website', '')
        restaurant.primary_color = request.POST.get('primary_color', restaurant.primary_color)
        restaurant.secondary_color = request.POST.get('secondary_color', restaurant.secondary_color)
        restaurant.default_currency = request.POST.get('currency', 'USD')
        
        # Handle is_active checkbox -> status field
        is_active = request.POST.get('is_active') == 'on'
        if is_active:
            restaurant.status = Restaurant.Status.ACTIVE
        else:
            restaurant.status = Restaurant.Status.INACTIVE
        
        # Handle ordering_enabled checkbox
        restaurant.ordering_enabled = request.POST.get('ordering_enabled') == 'on'
        
        if 'logo' in request.FILES:
            restaurant.logo = request.FILES['logo']
        if 'cover_image' in request.FILES:
            restaurant.cover_image = request.FILES['cover_image']
        
        restaurant.save()
        messages.success(request, 'Restaurant settings updated!')
        return redirect('restaurant-settings', restaurant_id=restaurant.id)
    
    context = {
        'restaurant': restaurant,
    }
    return render(request, 'dashboard/restaurants/settings.html', context)


# Menu Management Views
@login_required
def menu_list(request):
    """List all menus for the selected restaurant."""
    from apps.menus.models import Menu
    from apps.restaurants.models import Restaurant
    
    restaurant_id = request.session.get('selected_restaurant_id')
    if not restaurant_id:
        messages.warning(request, 'Please select or create a restaurant first.')
        return redirect('restaurant-create')
    
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    menus = Menu.objects.filter(restaurant=restaurant).order_by('-is_active', 'name')
    
    context = {
        'restaurant': restaurant,
        'menus': menus,
    }
    return render(request, 'dashboard/menus/list.html', context)


@login_required
def menu_create(request):
    """Create a new menu."""
    from apps.menus.models import Menu
    from apps.restaurants.models import Restaurant
    
    restaurant_id = request.session.get('selected_restaurant_id')
    if not restaurant_id:
        messages.warning(request, 'Please select or create a restaurant first.')
        return redirect('restaurant-create')
    
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        
        if not name:
            messages.error(request, 'Menu name is required.')
            return render(request, 'dashboard/menus/create.html', {'restaurant': restaurant})
        
        menu = Menu.objects.create(
            restaurant=restaurant,
            name=name,
            description=description,
            is_active=True
        )
        messages.success(request, f'Menu "{name}" created successfully!')
        return redirect('menu-detail', menu_id=menu.id)
    
    context = {
        'restaurant': restaurant,
    }
    return render(request, 'dashboard/menus/create.html', context)


@login_required
def menu_detail(request, menu_id):
    """Menu detail with categories and items."""
    from apps.menus.models import Menu, Category, MenuItem
    
    menu = get_object_or_404(Menu.objects.select_related('restaurant'), id=menu_id)
    categories = Category.objects.filter(menu=menu).prefetch_related('items').order_by('position')
    
    context = {
        'menu': menu,
        'restaurant': menu.restaurant,
        'categories': categories,
    }
    return render(request, 'dashboard/menus/detail.html', context)


@login_required
def category_create(request, menu_id):
    """Create a new category in a menu."""
    from apps.menus.models import Menu, Category
    
    menu = get_object_or_404(Menu, id=menu_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        
        if not name:
            messages.error(request, 'Category name is required.')
            return redirect('menu-detail', menu_id=menu.id)
        
        # Get max position
        max_order = Category.objects.filter(menu=menu).aggregate(
            max_order=Max('position')
        )['max_order'] or 0

        Category.objects.create(
            menu=menu,
            name=name,
            description=description,
            position=max_order + 1
        )
        messages.success(request, f'Category "{name}" created!')
        return redirect('menu-detail', menu_id=menu.id)
    
    return redirect('menu-detail', menu_id=menu.id)


@login_required
def menu_item_create(request, menu_id, category_id):
    """Create a new menu item."""
    from apps.menus.models import Menu, Category, MenuItem
    
    menu = get_object_or_404(Menu, id=menu_id)
    category = get_object_or_404(Category, id=category_id, menu=menu)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        price = request.POST.get('price', '0')
        
        if not name:
            messages.error(request, 'Item name is required.')
            return redirect('menu-detail', menu_id=menu.id)
        
        try:
            price = Decimal(price)
        except:
            price = Decimal('0.00')
        
# Get max position
        max_order = MenuItem.objects.filter(category=category).aggregate(
            max_order=Max('position')
        )['max_order'] or 0

        item = MenuItem.objects.create(
            category=category,
            name=name,
            description=description,
            price=price,
            position=max_order + 1
        )
        
        if 'image' in request.FILES:
            item.image = request.FILES['image']
            item.save()
        
        messages.success(request, f'Item "{name}" added!')
        return redirect('menu-detail', menu_id=menu.id)
    
    context = {
        'menu': menu,
        'category': category,
        'restaurant': menu.restaurant,
    }
    return render(request, 'dashboard/menus/item_create.html', context)


@login_required 
def menu_item_edit(request, menu_id, item_id):
    """Edit a menu item."""
    from apps.menus.models import Menu, MenuItem
    
    menu = get_object_or_404(Menu, id=menu_id)
    item = get_object_or_404(MenuItem, id=item_id, category__menu=menu)
    
    if request.method == 'POST':
        item.name = request.POST.get('name', item.name)
        item.description = request.POST.get('description', '')
        
        try:
            item.price = Decimal(request.POST.get('price', '0'))
        except:
            pass
        
        # Update status based on checkbox
        if request.POST.get('is_available') == 'on':
            item.status = 'available'
        else:
            item.status = 'hidden'
        item.is_featured = request.POST.get('is_featured') == 'on'
        
        if 'image' in request.FILES:
            item.image = request.FILES['image']
        
        item.save()
        messages.success(request, f'Item "{item.name}" updated!')
        return redirect('menu-detail', menu_id=menu.id)
    
    context = {
        'menu': menu,
        'item': item,
        'restaurant': menu.restaurant,
    }
    return render(request, 'dashboard/menus/item_edit.html', context)


@login_required
def menu_item_delete(request, menu_id, item_id):
    """Delete a menu item."""
    from apps.menus.models import Menu, MenuItem
    
    menu = get_object_or_404(Menu, id=menu_id)
    item = get_object_or_404(MenuItem, id=item_id, category__menu=menu)
    
    if request.method == 'POST':
        name = item.name
        item.delete()
        messages.success(request, f'Item "{name}" deleted.')
    
    return redirect('menu-detail', menu_id=menu.id)


# Order Management Views
@login_required
def order_list(request):
    """List orders for the selected restaurant."""
    from apps.orders.models import Order
    from apps.restaurants.models import Restaurant
    
    restaurant_id = request.session.get('selected_restaurant_id')
    if not restaurant_id:
        messages.warning(request, 'Please select or create a restaurant first.')
        return redirect('restaurant-create')
    
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    orders = Order.objects.filter(restaurant=restaurant).select_related(
        'customer', 'location', 'table'
    ).order_by('-created_at')
    
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    context = {
        'restaurant': restaurant,
        'orders': orders[:50],  # Limit to last 50
        'status_filter': status_filter,
        'status_choices': Order.Status.choices,
    }
    return render(request, 'dashboard/orders/list.html', context)


@login_required
def order_detail(request, order_id):
    """Order detail view."""
    from apps.orders.models import Order, OrderItem
    
    restaurant_id = request.session.get('selected_restaurant_id')
    order = get_object_or_404(
        Order.objects.select_related('customer', 'location', 'table', 'restaurant'),
        id=order_id,
        restaurant_id=restaurant_id
    )
    items = OrderItem.objects.filter(order=order).select_related('menu_item')
    
    context = {
        'order': order,
        'items': items,
        'restaurant': order.restaurant,
        'status_choices': Order.Status.choices,
    }
    return render(request, 'dashboard/orders/detail.html', context)


@login_required
def order_update_status(request, order_id):
    """Update order status."""
    from apps.orders.models import Order
    
    if request.method == 'POST':
        restaurant_id = request.session.get('selected_restaurant_id')
        order = get_object_or_404(Order, id=order_id, restaurant_id=restaurant_id)
        
        new_status = request.POST.get('status')
        if new_status in dict(Order.Status.choices):
            order.status = new_status
            order.save()
            messages.success(request, f'Order #{order.order_number} status updated to {order.get_status_display()}')
        else:
            messages.error(request, 'Invalid status.')
    
    return redirect('order-detail', order_id=order_id)


# QR Code Management Views
@login_required
def qrcode_list(request):
    """List QR codes for the selected restaurant with filtering and stats."""
    from apps.qrcodes.models import QRCode
    from apps.restaurants.models import Restaurant, Location, Table
    
    restaurant_id = request.session.get('selected_restaurant_id')
    if not restaurant_id:
        messages.warning(request, 'Please select or create a restaurant first.')
        return redirect('restaurant-create')
    
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    
    # Base queryset
    qr_codes = QRCode.objects.filter(restaurant=restaurant).select_related(
        'menu', 'location', 'table'
    )
    
    # Filters
    search = request.GET.get('search', '').strip()
    qr_type = request.GET.get('type', '')
    location_id = request.GET.get('location', '')
    status = request.GET.get('status', '')
    
    if search:
        qr_codes = qr_codes.filter(
            Q(name__icontains=search) | 
            Q(short_code__icontains=search) |
            Q(table__number__icontains=search)
        )
    
    if qr_type:
        qr_codes = qr_codes.filter(qr_type=qr_type)
    
    if location_id:
        qr_codes = qr_codes.filter(location_id=location_id)
    
    if status == 'active':
        qr_codes = qr_codes.filter(is_active=True)
    elif status == 'inactive':
        qr_codes = qr_codes.filter(is_active=False)
    
    qr_codes = qr_codes.order_by('-created_at')
    
    # Get stats
    all_qr_codes = QRCode.objects.filter(restaurant=restaurant)
    stats = {
        'total': all_qr_codes.count(),
        'active': all_qr_codes.filter(is_active=True).count(),
        'inactive': all_qr_codes.filter(is_active=False).count(),
        'total_scans': all_qr_codes.aggregate(total=Sum('scan_count'))['total'] or 0,
    }
    
    # Get available locations and QR types for filters
    locations = Location.objects.filter(restaurant=restaurant)
    qr_types = QRCode.TYPE_CHOICES
    
    context = {
        'restaurant': restaurant,
        'qrcodes': qr_codes,
        'stats': stats,
        'locations': locations,
        'qr_types': qr_types,
        'filters': {
            'search': search,
            'type': qr_type,
            'location': location_id,
            'status': status,
        }
    }
    return render(request, 'dashboard/qrcodes/list.html', context)


@login_required
def qrcode_toggle_status(request, qrcode_id):
    """Toggle QR code active status."""
    from apps.qrcodes.models import QRCode
    
    if request.method == 'POST':
        qr_code = get_object_or_404(QRCode, id=qrcode_id)
        qr_code.is_active = not qr_code.is_active
        qr_code.save()
        status_text = 'activated' if qr_code.is_active else 'deactivated'
        messages.success(request, f'QR Code "{qr_code.name}" {status_text}.')
    
    return redirect('qrcode-list')


@login_required
def qrcode_delete(request, qrcode_id):
    """Delete a QR code."""
    from apps.qrcodes.models import QRCode
    
    if request.method == 'POST':
        qr_code = get_object_or_404(QRCode, id=qrcode_id)
        name = qr_code.name
        qr_code.delete()
        messages.success(request, f'QR Code "{name}" deleted.')
    
    return redirect('qrcode-list')


@login_required
def qrcode_regenerate(request, qrcode_id):
    """Regenerate QR code image."""
    from apps.qrcodes.models import QRCode
    
    if request.method == 'POST':
        qr_code = get_object_or_404(QRCode, id=qrcode_id)
        try:
            qr_code.generate_qr_image()
            qr_code.save()
            messages.success(request, f'QR Code "{qr_code.name}" regenerated.')
        except Exception as e:
            messages.error(request, f'Failed to regenerate QR code: {e}')
    
    return redirect('qrcode-list')


@login_required
def qrcode_bulk_action(request):
    """Handle bulk actions on QR codes."""
    from apps.qrcodes.models import QRCode
    import zipfile
    from io import BytesIO
    from django.http import HttpResponse
    
    if request.method == 'POST':
        action = request.POST.get('action')
        qrcode_ids = request.POST.getlist('qrcode_ids')
        
        if not qrcode_ids:
            messages.warning(request, 'Please select at least one QR code.')
            return redirect('qrcode-list')
        
        qr_codes = QRCode.objects.filter(id__in=qrcode_ids)
        
        if action == 'activate':
            count = qr_codes.update(is_active=True)
            messages.success(request, f'{count} QR code(s) activated.')
        
        elif action == 'deactivate':
            count = qr_codes.update(is_active=False)
            messages.success(request, f'{count} QR code(s) deactivated.')
        
        elif action == 'delete':
            count = qr_codes.count()
            qr_codes.delete()
            messages.success(request, f'{count} QR code(s) deleted.')
        
        elif action == 'download':
            # Create ZIP file with all QR codes
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for qr in qr_codes:
                    if qr.qr_image:
                        try:
                            filename = f"{qr.name.replace(' ', '_')}_{qr.short_code}.png"
                            zip_file.writestr(filename, qr.qr_image.read())
                        except Exception:
                            pass
            
            zip_buffer.seek(0)
            response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
            response['Content-Disposition'] = 'attachment; filename="qr_codes.zip"'
            return response
    
    return redirect('qrcode-list')


@login_required
def qrcode_create(request):
    """Create a new QR code."""
    from apps.qrcodes.models import QRCode
    from apps.restaurants.models import Restaurant, Location, Table
    from apps.menus.models import Menu
    import secrets
    
    restaurant_id = request.session.get('selected_restaurant_id')
    if not restaurant_id:
        messages.warning(request, 'Please select or create a restaurant first.')
        return redirect('restaurant-create')
    
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    menus = Menu.objects.filter(restaurant=restaurant, is_active=True)
    locations = Location.objects.filter(restaurant=restaurant)
    tables = Table.objects.filter(location__restaurant=restaurant).select_related('location')
    
    if request.method == 'POST':
        qr_type = request.POST.get('qr_type', 'menu')
        name = request.POST.get('name', '')
        menu_id = request.POST.get('menu')
        location_id = request.POST.get('location')
        table_id = request.POST.get('table')
        is_active = request.POST.get('is_active') == '1'
        
        # WiFi specific fields
        wifi_ssid = request.POST.get('wifi_ssid', '')
        wifi_password = request.POST.get('wifi_password', '')
        wifi_encryption = request.POST.get('wifi_encryption', 'WPA')
        
        # Custom URL field
        custom_url = request.POST.get('custom_url', '')
        
        # Validation
        if not name:
            messages.error(request, 'QR code name is required.')
            return render(request, 'dashboard/qrcodes/create.html', {
                'restaurant': restaurant, 'menus': menus, 
                'locations': locations, 'tables': tables
            })
        
        if qr_type == 'wifi' and not wifi_ssid:
            messages.error(request, 'WiFi network name (SSID) is required.')
            return render(request, 'dashboard/qrcodes/create.html', {
                'restaurant': restaurant, 'menus': menus, 
                'locations': locations, 'tables': tables
            })
        
        if qr_type == 'custom' and not custom_url:
            messages.error(request, 'Custom URL is required.')
            return render(request, 'dashboard/qrcodes/create.html', {
                'restaurant': restaurant, 'menus': menus, 
                'locations': locations, 'tables': tables
            })
        
        # Generate short code (6 bytes = 8 chars base64, truncate to 10)
        short_code = secrets.token_urlsafe(6)[:10]
        
        qr_code = QRCode.objects.create(
            restaurant=restaurant,
            short_code=short_code,
            qr_type=qr_type,
            name=name,
            menu_id=menu_id if menu_id else None,
            location_id=location_id if location_id else None,
            table_id=table_id if table_id else None,
            is_active=is_active,
            wifi_ssid=wifi_ssid,
            wifi_password=wifi_password,
            wifi_encryption=wifi_encryption,
            custom_url=custom_url,
        )
        
        # Generate QR code image
        try:
            qr_code.generate_qr_image()
            qr_code.save()
        except Exception as e:
            messages.warning(request, f'QR Code created but image generation failed: {e}')
        
        messages.success(request, f'QR Code "{qr_code.name}" created successfully!')
        return redirect('qrcode-list')
    
    context = {
        'restaurant': restaurant,
        'menus': menus,
        'locations': locations,
        'tables': tables,
    }
    return render(request, 'dashboard/qrcodes/create.html', context)


# Location Management
@login_required
def location_list(request):
    """List locations for the selected restaurant."""
    from apps.restaurants.models import Restaurant, Location
    
    restaurant_id = request.session.get('selected_restaurant_id')
    if not restaurant_id:
        messages.warning(request, 'Please select or create a restaurant first.')
        return redirect('restaurant-create')
    
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    locations = Location.objects.filter(restaurant=restaurant).order_by('name')
    
    context = {
        'restaurant': restaurant,
        'locations': locations,
    }
    return render(request, 'dashboard/locations/list.html', context)


@login_required
def location_create(request):
    """Create a new location."""
    from apps.restaurants.models import Restaurant, Location
    
    restaurant_id = request.session.get('selected_restaurant_id')
    if not restaurant_id:
        messages.warning(request, 'Please select or create a restaurant first.')
        return redirect('restaurant-create')
    
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        address = request.POST.get('address', '')
        city = request.POST.get('city', '')
        state = request.POST.get('state', '')
        country = request.POST.get('country', '')
        postal_code = request.POST.get('postal_code', '')
        phone = request.POST.get('phone', '')
        email = request.POST.get('email', '')
        
        if not name:
            messages.error(request, 'Location name is required.')
            return render(request, 'dashboard/locations/create.html', {'restaurant': restaurant})
        
        Location.objects.create(
            restaurant=restaurant,
            name=name,
            address_line1=address,
            city=city,
            state=state,
            country=country,
            postal_code=postal_code,
            phone=phone,
            email=email,
        )
        messages.success(request, f'Location "{name}" created!')
        return redirect('location-list')
    
    context = {
        'restaurant': restaurant,
    }
    return render(request, 'dashboard/locations/create.html', context)


# Theme Customization Views
@login_required
def theme_customize(request):
    """Theme customization page for restaurant menu appearance."""
    from apps.restaurants.models import Restaurant, RestaurantTheme
    
    restaurant_id = request.session.get('selected_restaurant_id')
    if not restaurant_id:
        messages.warning(request, 'Please select or create a restaurant first.')
        return redirect('restaurant-create')
    
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    
    # Get or create theme
    theme, created = RestaurantTheme.objects.get_or_create(
        restaurant=restaurant,
        defaults={
            'primary_color': restaurant.primary_color or '#E11D48',
            'secondary_color': restaurant.secondary_color or '#1E293B',
        }
    )
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Apply preset if requested
        if action == 'apply_preset':
            preset_name = request.POST.get('preset')
            preset_values = RestaurantTheme.get_preset(preset_name)
            for key, value in preset_values.items():
                setattr(theme, key, value)
            theme.preset_name = preset_name
            theme.save()
            messages.success(request, f'Preset "{preset_name.replace("_", " ").title()}" applied!')
            return redirect('theme-customize')
        
        # Save theme settings
        # Layout & Style
        theme.layout_style = request.POST.get('layout_style', theme.layout_style)
        theme.header_style = request.POST.get('header_style', theme.header_style)
        theme.card_style = request.POST.get('card_style', theme.card_style)
        
        # Colors
        theme.primary_color = request.POST.get('primary_color', theme.primary_color)
        theme.secondary_color = request.POST.get('secondary_color', theme.secondary_color)
        theme.accent_color = request.POST.get('accent_color', theme.accent_color)
        theme.background_color = request.POST.get('background_color', theme.background_color)
        theme.surface_color = request.POST.get('surface_color', theme.surface_color)
        theme.card_background = request.POST.get('card_background', theme.card_background)
        theme.text_primary = request.POST.get('text_primary', theme.text_primary)
        theme.text_secondary = request.POST.get('text_secondary', theme.text_secondary)
        theme.text_on_primary = request.POST.get('text_on_primary', theme.text_on_primary)
        
        # Typography
        theme.heading_font = request.POST.get('heading_font', theme.heading_font)
        theme.body_font = request.POST.get('body_font', theme.body_font)
        theme.price_font = request.POST.get('price_font', theme.price_font)
        
        # Spacing & Radius
        theme.border_radius = request.POST.get('border_radius', theme.border_radius)
        
        # Hero Section
        theme.hero_overlay_opacity = int(request.POST.get('hero_overlay_opacity', theme.hero_overlay_opacity))
        theme.hero_text_color = request.POST.get('hero_text_color', theme.hero_text_color)
        theme.hero_height = request.POST.get('hero_height', theme.hero_height)
        
        if 'hero_image' in request.FILES:
            theme.hero_image = request.FILES['hero_image']
        
        # Display Options
        theme.show_prices = 'show_prices' in request.POST
        theme.show_images = 'show_images' in request.POST
        theme.show_descriptions = 'show_descriptions' in request.POST
        theme.show_dietary_badges = 'show_dietary_badges' in request.POST
        theme.show_popular_badge = 'show_popular_badge' in request.POST
        theme.show_search = 'show_search' in request.POST
        theme.show_category_images = 'show_category_images' in request.POST
        theme.show_social_links = 'show_social_links' in request.POST
        theme.show_contact_info = 'show_contact_info' in request.POST
        
        # Cart & Ordering
        theme.enable_cart = 'enable_cart' in request.POST
        theme.floating_cart_button = 'floating_cart_button' in request.POST
        
        # Animations
        theme.enable_animations = 'enable_animations' in request.POST
        theme.enable_smooth_scroll = 'enable_smooth_scroll' in request.POST
        
        # Custom CSS
        theme.custom_css = request.POST.get('custom_css', '')
        
        theme.preset_name = ''  # Clear preset when manually customizing
        theme.save()
        messages.success(request, 'Theme settings saved!')
        return redirect('theme-customize')
    
    # Get all QR codes for preview
    from apps.qrcodes.models import QRCode
    qr_code = QRCode.objects.filter(restaurant=restaurant, is_active=True).first()
    
    # Font options
    font_options = [
        'Inter', 'Playfair Display', 'DM Sans', 'Poppins', 'Montserrat',
        'Roboto', 'Open Sans', 'Lato', 'Nunito', 'Fredoka One',
        'Space Grotesk', 'Cormorant Garamond', 'Merriweather', 'Raleway',
        'Source Sans Pro', 'Ubuntu', 'Work Sans', 'Oswald', 'Rubik', 'Quicksand'
    ]
    
    # Preset options
    presets = [
        {'id': 'modern_minimal', 'name': 'Modern Minimal', 'icon': '🎯'},
        {'id': 'elegant_luxury', 'name': 'Elegant Luxury', 'icon': '✨'},
        {'id': 'casual_fun', 'name': 'Casual & Fun', 'icon': '🎨'},
        {'id': 'dark_mode', 'name': 'Dark Mode', 'icon': '🌙'},
        {'id': 'vibrant_bold', 'name': 'Vibrant Bold', 'icon': '🔥'},
    ]
    
    context = {
        'restaurant': restaurant,
        'theme': theme,
        'qr_code': qr_code,
        'font_options': font_options,
        'presets': presets,
        'layout_styles': RestaurantTheme.LayoutStyle.choices,
        'header_styles': RestaurantTheme.HeaderStyle.choices,
        'card_styles': RestaurantTheme.CardStyle.choices,
    }
    return render(request, 'dashboard/theme/customize.html', context)


# Table Management
@login_required
def table_list(request):
    """List tables for the selected restaurant."""
    from apps.restaurants.models import Restaurant, Location, Table
    
    restaurant_id = request.session.get('selected_restaurant_id')
    if not restaurant_id:
        messages.warning(request, 'Please select or create a restaurant first.')
        return redirect('restaurant-create')
    
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    tables = Table.objects.filter(location__restaurant=restaurant).select_related('location').order_by('location__name', 'number')
    locations = Location.objects.filter(restaurant=restaurant)
    
    context = {
        'restaurant': restaurant,
        'tables': tables,
        'locations': locations,
    }
    return render(request, 'dashboard/tables/list.html', context)


@login_required
def table_create(request):
    """Create a new table or multiple tables."""
    from apps.restaurants.models import Restaurant, Location, Table
    
    restaurant_id = request.session.get('selected_restaurant_id')
    if not restaurant_id:
        messages.warning(request, 'Please select or create a restaurant first.')
        return redirect('restaurant-create')
    
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    locations = Location.objects.filter(restaurant=restaurant)
    
    if request.method == 'POST':
        location_id = request.POST.get('location')
        creation_mode = request.POST.get('creation_mode', 'single')
        capacity = request.POST.get('capacity', 4)
        prefix = request.POST.get('prefix', '').strip()
        
        if not location_id:
            messages.error(request, 'Please select a location.')
            return render(request, 'dashboard/tables/create.html', {'restaurant': restaurant, 'locations': locations})
        
        location = get_object_or_404(Location, id=location_id, restaurant=restaurant)
        
        try:
            capacity = int(capacity)
        except ValueError:
            capacity = 4
        
        tables_created = []
        tables_skipped = []
        
        if creation_mode == 'single':
            # Single table creation
            number = request.POST.get('number', '').strip()
            name = request.POST.get('name', '').strip()
            
            if not number:
                messages.error(request, 'Table number is required.')
                return render(request, 'dashboard/tables/create.html', {'restaurant': restaurant, 'locations': locations})
            
            full_number = f"{prefix}{number}" if prefix else number
            
            if Table.objects.filter(location=location, number=full_number).exists():
                messages.error(request, f'Table {full_number} already exists at this location.')
                return render(request, 'dashboard/tables/create.html', {'restaurant': restaurant, 'locations': locations})
            
            Table.objects.create(
                location=location,
                number=full_number,
                name=name,
                capacity=capacity,
            )
            messages.success(request, f'Table {full_number} created successfully!')
            
        elif creation_mode == 'range':
            # Range creation (e.g., 1-10)
            start_num = request.POST.get('range_start', '1')
            end_num = request.POST.get('range_end', '10')
            
            try:
                start = int(start_num)
                end = int(end_num)
            except ValueError:
                messages.error(request, 'Please enter valid numbers for the range.')
                return render(request, 'dashboard/tables/create.html', {'restaurant': restaurant, 'locations': locations})
            
            if start > end:
                start, end = end, start
            
            if end - start > 100:
                messages.error(request, 'Maximum 100 tables can be created at once.')
                return render(request, 'dashboard/tables/create.html', {'restaurant': restaurant, 'locations': locations})
            
            for num in range(start, end + 1):
                full_number = f"{prefix}{num}" if prefix else str(num)
                
                if Table.objects.filter(location=location, number=full_number).exists():
                    tables_skipped.append(full_number)
                    continue
                
                Table.objects.create(
                    location=location,
                    number=full_number,
                    name='',
                    capacity=capacity,
                )
                tables_created.append(full_number)
            
            if tables_created:
                messages.success(request, f'Created {len(tables_created)} tables: {", ".join(tables_created[:5])}{"..." if len(tables_created) > 5 else ""}')
            if tables_skipped:
                messages.warning(request, f'Skipped {len(tables_skipped)} existing tables: {", ".join(tables_skipped[:5])}{"..." if len(tables_skipped) > 5 else ""}')
                
        elif creation_mode == 'multiple':
            # Multiple specific numbers (e.g., "1, 2, 3, VIP-1, VIP-2")
            numbers_input = request.POST.get('table_numbers', '')
            
            # Parse numbers - split by comma, newline, or space
            import re
            numbers = [n.strip() for n in re.split(r'[,\n\s]+', numbers_input) if n.strip()]
            
            if not numbers:
                messages.error(request, 'Please enter at least one table number.')
                return render(request, 'dashboard/tables/create.html', {'restaurant': restaurant, 'locations': locations})
            
            if len(numbers) > 100:
                messages.error(request, 'Maximum 100 tables can be created at once.')
                return render(request, 'dashboard/tables/create.html', {'restaurant': restaurant, 'locations': locations})
            
            for number in numbers:
                full_number = f"{prefix}{number}" if prefix else number
                
                if Table.objects.filter(location=location, number=full_number).exists():
                    tables_skipped.append(full_number)
                    continue
                
                Table.objects.create(
                    location=location,
                    number=full_number,
                    name='',
                    capacity=capacity,
                )
                tables_created.append(full_number)
            
            if tables_created:
                messages.success(request, f'Created {len(tables_created)} tables: {", ".join(tables_created[:5])}{"..." if len(tables_created) > 5 else ""}')
            if tables_skipped:
                messages.warning(request, f'Skipped {len(tables_skipped)} existing tables: {", ".join(tables_skipped[:5])}{"..." if len(tables_skipped) > 5 else ""}')
        
        return redirect('table-list')
    
    context = {
        'restaurant': restaurant,
        'locations': locations,
    }
    return render(request, 'dashboard/tables/create.html', context)


@login_required
def table_delete(request, table_id):
    """Delete a table."""
    from apps.restaurants.models import Restaurant, Table
    
    restaurant_id = request.session.get('selected_restaurant_id')
    if not restaurant_id:
        messages.warning(request, 'Please select or create a restaurant first.')
        return redirect('restaurant-create')
    
    table = get_object_or_404(Table, id=table_id, location__restaurant_id=restaurant_id)
    
    if request.method == 'POST':
        table_number = table.number
        table.delete()
        messages.success(request, f'Table {table_number} deleted successfully!')
    
    return redirect('table-list')


@login_required
def table_bulk_action(request):
    """Handle bulk actions on tables."""
    from apps.restaurants.models import Restaurant, Table
    from apps.qrcodes.models import QRCode
    import secrets
    
    if request.method != 'POST':
        return redirect('table-list')
    
    restaurant_id = request.session.get('selected_restaurant_id')
    if not restaurant_id:
        return redirect('restaurant-create')
    
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    action = request.POST.get('bulk_action')
    table_ids = request.POST.getlist('table_ids')
    
    if not table_ids:
        messages.warning(request, 'Please select at least one table.')
        return redirect('table-list')
    
    tables = Table.objects.filter(id__in=table_ids, location__restaurant=restaurant)
    count = tables.count()
    
    if action == 'delete':
        tables.delete()
        messages.success(request, f'Deleted {count} tables.')
        
    elif action == 'set_available':
        tables.update(status='available')
        messages.success(request, f'Marked {count} tables as available.')
        
    elif action == 'set_occupied':
        tables.update(status='occupied')
        messages.success(request, f'Marked {count} tables as occupied.')
        
    elif action == 'set_reserved':
        tables.update(status='reserved')
        messages.success(request, f'Marked {count} tables as reserved.')
        
    elif action == 'set_unavailable':
        tables.update(status='unavailable')
        messages.success(request, f'Marked {count} tables as unavailable.')
        
    elif action == 'generate_qr':
        # Generate QR codes for tables that don't have one
        from apps.menus.models import Menu
        
        qr_created = 0
        qr_skipped = 0
        
        for table in tables:
            # Check if QR code already exists for this table
            if QRCode.objects.filter(restaurant=restaurant, table=table).exists():
                qr_skipped += 1
                continue
            
            # Generate short code
            short_code = secrets.token_urlsafe(6)[:10]
            
            # Get default menu
            menu = Menu.objects.filter(restaurant=restaurant, is_active=True).first()
            
            qr_code = QRCode.objects.create(
                restaurant=restaurant,
                location=table.location,
                table=table,
                short_code=short_code,
                qr_type='table',
                name=f'Table {table.number}',
                menu=menu,
            )
            
            # Generate QR code image
            try:
                qr_code.generate_qr_image()
                qr_code.save()
            except Exception:
                pass
            
            qr_created += 1
        
        if qr_created:
            messages.success(request, f'Generated QR codes for {qr_created} tables.')
        if qr_skipped:
            messages.info(request, f'Skipped {qr_skipped} tables that already have QR codes.')
    
    return redirect('table-list')


@login_required
def table_update_status(request, table_id):
    """Update a single table's status."""
    from apps.restaurants.models import Table
    
    restaurant_id = request.session.get('selected_restaurant_id')
    if not restaurant_id:
        return JsonResponse({'error': 'No restaurant selected'}, status=400)
    
    table = get_object_or_404(Table, id=table_id, location__restaurant_id=restaurant_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['available', 'occupied', 'reserved', 'unavailable']:
            table.status = new_status
            table.save()
            messages.success(request, f'Table {table.number} is now {table.get_status_display()}.')
    
    return redirect('table-list')


# API endpoints for AJAX updates
@login_required
def api_dashboard_stats(request):
    """API endpoint for real-time dashboard stats."""
    from apps.orders.models import Order
    from apps.qrcodes.models import QRCodeScan
    
    restaurant_id = request.session.get('selected_restaurant_id')
    if not restaurant_id:
        return JsonResponse({'error': 'No restaurant selected'}, status=400)
    
    today = timezone.now().date()
    
    orders = Order.objects.filter(restaurant_id=restaurant_id)
    pending_orders = orders.filter(status__in=['pending', 'confirmed', 'preparing']).count()
    orders_today = orders.filter(created_at__date=today).count()
    
    revenue_today = orders.filter(
        status__in=['completed', 'delivered', 'picked_up'],
        created_at__date=today
    ).aggregate(total=Sum('total'))['total'] or 0
    
    scans_today = QRCodeScan.objects.filter(
        qr_code__restaurant_id=restaurant_id,
        scanned_at__date=today
    ).count()
    
    return JsonResponse({
        'pending_orders': pending_orders,
        'orders_today': orders_today,
        'revenue_today': float(revenue_today),
        'scans_today': scans_today,
    })
