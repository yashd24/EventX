from EventX.helper import BaseAPIClass
from accounts.serializers import LoginSerializer, SignUpSerializer
from accounts.models import User, UserActiveSession, UserSessionDump
from EventX.utils import generate_jwt_token


class SignUpView(BaseAPIClass):
    model_class = User
    signup_serializer = SignUpSerializer
    
    def post(self, request):
        try:
            serializer = self.signup_serializer(data=request.data)
            if serializer.is_valid():
                email = serializer.validated_data['email']
                name = serializer.validated_data['name']
                password = serializer.validated_data['password']
                user_type = serializer.validated_data['user_type']

                # Check if user already exists
                if self.model_class.objects.filter(email=email).exists():
                    self.message = "User already exists"
                    self.error_occurred(e=None, custom_code=1104)
                    return self.get_response()

                # Create user with hashed password
                user = self.model_class(
                    email=email, 
                    name=name,
                    user_type=user_type
                )
                user.set_password(password)
                user.save()

                self.data = {
                    "user_id": str(user.user_id),
                    "email": user.email,
                    "name": user.name,
                    "user_type": user.user_type.name,
                    "created_at": user.created_at.isoformat(),
                    "updated_at": user.updated_at.isoformat()
                }

                self.message = "Sign up successful"
            else: 
                self.serializer_errors(serializer.errors)
                self.custom_code = 1101
        except Exception as e:
            self.message="Sign up failed"
            self.error_occurred(e, custom_code=1102)
        return self.get_response()


class LoginView(BaseAPIClass):
    model_class = User
    login_serializer = LoginSerializer
    
    def post(self, request):
        try:
            serializer = self.login_serializer(data=request.data)
            if serializer.is_valid():
                email = serializer.validated_data['email']
                password = serializer.validated_data['password']
                
                try:
                    user = self.model_class.objects.get(email=email)
                    
                    if not user.check_password(password):
                        self.message = "Invalid password"
                        self.error_occurred(e=None, custom_code=1203)
                        return self.get_response()
                    
                    # Generate JWT access token
                    access_token = generate_jwt_token(user.user_id, user.email, user.name)

                    # Create or update active session
                    session, created = UserActiveSession.objects.get_or_create(
                        user_id=user,
                        defaults={'access_token': access_token}
                    )
                    print("Created:: ",created)
                    if not created:
                        # Update existing session with new token
                        session.access_token = access_token
                        session.save()
                    print("Session:: ",session)
                    # Prepare response data
                    self.data = {
                        'user_id': str(user.user_id),
                        'email': user.email,
                        'name': user.name,
                        'access_token': access_token,
                        'token_type': 'Bearer'
                    }
                    self.message = "Login successful"
                                        
                except self.model_class.DoesNotExist:
                    self.message = "User not found"
                    self.error_occurred(e=None, custom_code=1201)
            else:
                self._serializer_errors(serializer.errors)
        except Exception as e:
            self.error_occurred(e, message="Login failed", custom_code=1202)
        return self.get_response()


class LogoutView(BaseAPIClass):
    def post(self, request):
        try:
            # Get JWT token from request headers or data
            access_token = request.headers.get('Authorization', '').replace('Bearer ', '')
            
            if access_token:
                # Delete the active session
                user_session = UserActiveSession.objects.get(access_token=access_token)
                UserSessionDump.objects.create(
                    user_id=user_session.user_id,
                    access_token=access_token,
                    login_datetime=user_session.created_at,
                )
                user_session.delete()

                self.message = "Logout successful"
            else:
                self.message = "Invalid or expired token"
                self.error_occurred(e=None, custom_code=1106)
        except Exception as e:
            self.message = "Logout failed"
            self.error_occurred(e, custom_code=1108)
        return self.get_response()


class ProfileView(BaseAPIClass):
    def get(self, request):
        """
        Get user profile
        """
        try:
            # Get validated user from middleware
            user = request.validated_user
            
            self.data = {
                'user_id': str(user.user_id),
                'email': user.email,
                'name': user.name,
                'user_type': user.user_type,
                'created_at': user.created_at.isoformat(),
                'updated_at': user.updated_at.isoformat(),
                'status': user.status
            }
            self.message = "Profile retrieved successfully"
            
        except Exception as e:
            self.message = "Failed to retrieve profile"
            self.error_occurred(e, custom_code=1110)
        return self.get_response()