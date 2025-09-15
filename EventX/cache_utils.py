"""
Ultra-simple caching utilities for EventX application
"""
from hashlib import md5
from django.conf import settings
from django.core.cache import cache
from rest_framework.response import Response


def get_cache_key(prefix: str, *args) -> str:
    """Generate a simple cache key"""
    key_parts = [str(prefix)]
    for arg in args:
        if arg is not None:
            key_parts.append(str(arg))
    
    cache_key = ":".join(key_parts)
    if len(cache_key) > 200:
        cache_key = f"{prefix}:{md5(cache_key.encode()).hexdigest()}"
    
    return cache_key


def get_cached_data(cache_key: str):
    """Get data from cache"""
    cached_data = cache.get(cache_key)
    if cached_data:
        print(f"[✅ Cache-Hit] {cache_key}")
    else:
        print(f"[❌ Cache-Miss] {cache_key}")
    return cached_data


def set_cached_data(cache_key: str, data, timeout: int = 300):
    """Set data in cache"""
    if not getattr(settings, 'ENABLE_CACHING', True):
        return
    
    cache.set(cache_key, data, timeout)
    print(f"[📅 Cache-Set] {cache_key} ({timeout}s)")


def delete_cache(cache_key: str):
    """Delete data from cache"""
    cache.delete(cache_key)
    print(f"[🗑️ Cache-Deleted] {cache_key}")


def cache_api_response(prefix: str, timeout: int = 300, vary_on_user: bool = False):
    """
    Ultra-simple decorator to cache API responses
    """
    def decorator(view_func):
        def wrapper(self, request, *args, **kwargs):
            # Build cache key
            key_parts = [prefix, request.path, request.method]
            
            # Add query params
            if request.GET:
                params_str = str(sorted(request.GET.items()))
                key_parts.append(md5(params_str.encode()).hexdigest()[:8])
            
            # Add user if needed
            if vary_on_user and hasattr(request, 'validated_user') and request.validated_user:
                key_parts.append(str(request.validated_user.user_id))
            
            cache_key = get_cache_key(*key_parts)
            
            # Try cache first
            cached_data = get_cached_data(cache_key)
            if cached_data:
                return Response(cached_data)
            
            # Execute view
            response = view_func(self, request, *args, **kwargs)
            
            # Cache if successful
            if hasattr(response, 'data') and response.data.get('success', False):
                set_cached_data(cache_key, response.data, timeout)
            
            return response
        
        return wrapper
    return decorator


# Simple cache invalidation functions
def invalidate_analytics_cache(event_id=None, venue_id=None):
    """Clear analytics cache"""
    if event_id:
        pattern = f"analytics:*{event_id}*"
        _clear_cache_pattern(pattern)
    if venue_id:
        pattern = f"analytics:*{venue_id}*"
        _clear_cache_pattern(pattern)


def invalidate_events_cache(event_id=None, venue_id=None):
    """Clear events cache"""
    if event_id:
        pattern = f"events:*{event_id}*"
        _clear_cache_pattern(pattern)
    if venue_id:
        pattern = f"events:*{venue_id}*"
        _clear_cache_pattern(pattern)


def invalidate_bookings_cache(user_id=None, event_id=None):
    """Clear bookings cache"""
    if user_id:
        pattern = f"bookings:*{user_id}*"
        _clear_cache_pattern(pattern)
    if event_id:
        pattern = f"bookings:*{event_id}*"
        _clear_cache_pattern(pattern)


def _clear_cache_pattern(pattern: str):
    """Clear cache entries matching pattern"""
    try:
        client = cache.client.get_client(write=True)
        keys = list(client.scan_iter(pattern))
        if keys:
            client.delete(*keys)
            print(f"[🗑️ Cache-Cleared] {len(keys)} keys matching {pattern}")
    except Exception as e:
        print(f"Cache clear error: {e}")
