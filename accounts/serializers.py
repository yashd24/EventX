from rest_framework import serializers

class SignUpSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    email = serializers.EmailField()
    password = serializers.CharField(max_length=128)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(max_length=128)

class FetchProfileSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()