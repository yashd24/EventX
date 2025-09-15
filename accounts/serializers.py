from rest_framework import serializers

from EventX.utils import validate_enum_str
from accounts.models import User

class SignUpSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    email = serializers.EmailField()
    password = serializers.CharField(max_length=128)
    user_type = serializers.CharField(max_length=10)

    def validate_user_type(self, value):
        return validate_enum_str(value, User.USER_TYPE)

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(max_length=128)

class FetchProfileSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()