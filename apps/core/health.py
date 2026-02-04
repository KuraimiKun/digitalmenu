"""Health check views for monitoring."""
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
@require_GET
def health_check(request):
    """Basic health check endpoint."""
    return JsonResponse({'status': 'healthy'})


@csrf_exempt
@require_GET
def health_check_detailed(request):
    """Detailed health check with dependencies."""
    health = {
        'status': 'healthy',
        'checks': {}
    }
    
    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        health['checks']['database'] = {'status': 'healthy'}
    except Exception as e:
        health['checks']['database'] = {'status': 'unhealthy', 'error': str(e)}
        health['status'] = 'unhealthy'
    
    # Redis/Cache check
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            health['checks']['cache'] = {'status': 'healthy'}
        else:
            health['checks']['cache'] = {'status': 'unhealthy', 'error': 'Cache read failed'}
            health['status'] = 'unhealthy'
    except Exception as e:
        health['checks']['cache'] = {'status': 'unhealthy', 'error': str(e)}
        health['status'] = 'unhealthy'
    
    status_code = 200 if health['status'] == 'healthy' else 503
    return JsonResponse(health, status=status_code)
