from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from EventX.utils import verify_jwt_token
from accounts.models import UserActiveSession, User


class ValidateTokenMiddleware(MiddlewareMixin):
    """
    Middleware that blocks requests if JWT access token is not validated
    """
    
    def process_request(self, request):
        """
        Block request if JWT token is not valid
        """
        # Skip authentication for certain paths
        skip_paths = [
            '/accounts/signup/',
            '/accounts/login/',
        ]
        
        # Check if current path should skip authentication
        for skip_path in skip_paths:
            if request.path.startswith(skip_path):
                return None
        
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return JsonResponse({
                'success': False,
                'message': 'Authorization header required',
                'status_code': 401
            }, status=401)
        
        token = auth_header.replace('Bearer ', '')
        
        if not token:
            return JsonResponse({
                'success': False,
                'message': 'Access token required',
                'status_code': 401
            }, status=401)
        
        try:
            # Verify JWT token
            payload = verify_jwt_token(token)
            if not payload:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid access token',
                    'status_code': 401
                }, status=401)
            
            # Check if token exists in active sessions
            try:
                session = UserActiveSession.objects.get(access_token=token)
                # Update last access time
                session.save()
                
                # Fetch the user and add to request
                user_id = payload['user_id']
                user = User.objects.get(user_id=user_id)
                request.validated_user = user
                request.user_payload = payload
                
            except UserActiveSession.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Token not found in active sessions',
                    'status_code': 401
                }, status=401)
            except User.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'User not found',
                    'status_code': 401
                }, status=401)
            print("Auth Completed")
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Authentication error: {str(e)}',
                'status_code': 401
            }, status=401)
        
        return None
