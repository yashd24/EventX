import jwt
import hashlib
from django.conf import settings
from datetime import datetime, timedelta
from accounts.models import UserActiveSession
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


def generate_password_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()


def generate_jwt_token(user_id, email, name):
    """
    Generate a JWT access token for the user
    """
    # Set token expiration from settings
    token_lifetime = getattr(settings, 'JWT_ACCESS_TOKEN_LIFETIME', 24)
    expiration_time = datetime.utcnow() + timedelta(hours=token_lifetime)
    
    # Create payload
    payload = {
        'user_id': str(user_id),
        'email': email,
        'name': name,
        'exp': expiration_time,
        'iat': datetime.utcnow(),
        'type': 'access'
    }
    
    # Generate token with secret key from settings
    secret_key = settings.JWT_SECRET_KEY
    token = jwt.encode(payload, secret_key, algorithm='HS256')    
    return token


def verify_jwt_token(token):
    """
    Verify and decode a JWT token
    """
    try:
        secret_key = settings.JWT_SECRET_KEY
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_user_from_token(request):
    """
    Extract and verify user from JWT token in request
    """
    # Get token from Authorization header
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None, "Missing or invalid Authorization header"
    
    token = auth_header.replace('Bearer ', '')
    if not token:
        return None, "Missing token"
    
    # Verify token
    payload = verify_jwt_token(token)
    if not payload:
        return None, "Invalid or expired token"
    
    # Check if token exists in active sessions
    try:
        session = UserActiveSession.objects.get(access_token=token)
        return payload, None
    except UserActiveSession.DoesNotExist:
        return None, "Session not found or expired"

def paginate_queryset(queryset, page, rows_per_page):
    """Paginate a queryset and return the requested page of results."""
    # Create a Paginator obj
    paginator = Paginator(queryset, rows_per_page)
    try:
        recs = paginator.page(page) # Get the requested page of activities
    except PageNotAnInteger:
        recs = paginator.page(1)  # If page is not an integer, deliver the first page.
    except EmptyPage:
        recs = paginator.page(paginator.num_pages)  # If page is out of range, deliver last page.
    
    return recs, paginator.count