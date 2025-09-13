# Example of how to use the JWT Middleware in your views

from EventX.helper import BaseAPIClass

class ExampleProtectedView(BaseAPIClass):
    """
    Example view that uses JWT middleware for authentication
    """
    
    def get(self, request):
        """
        This view is automatically protected by the middleware
        The middleware will:
        1. Check for JWT token in Authorization header
        2. Validate the token
        3. Add user information to request.user_payload
        4. Set request.is_authenticated = True
        """
        
        # Access user information (set by middleware)
        user_id = request.user_payload['user_id']
        email = request.user_payload['email']
        name = request.user_payload['name']
        
        # Access the active session (set by middleware)
        session = request.user_session
        
        self.data = {
            'message': f'Hello {name}!',
            'user_id': user_id,
            'email': email,
            'session_id': str(session.user_active_session_id),
            'last_access': session.last_access_datetime.isoformat()
        }
        self.message = "Protected endpoint accessed successfully"
        
        return self.get_response()

class ExamplePublicView(BaseAPIClass):
    """
    Example view that doesn't require authentication
    """
    
    def get(self, request):
        """
        This view is public - no authentication required
        """
        self.data = {
            'message': 'This is a public endpoint',
            'authenticated': getattr(request, 'is_authenticated', False)
        }
        self.message = "Public endpoint accessed"
        
        return self.get_response()
