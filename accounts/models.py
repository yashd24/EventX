from uuid import uuid4
from django.db import models
from django_enumfield import enum
from django.contrib.auth.hashers import make_password, check_password

class User(models.Model):
    class Meta:
        db_table = "user"

    class USER_STATUS(enum.Enum):
        ACTIVE = 1
        INACTIVE = 2    

    class USER_TYPE(enum.Enum):
        USER = 1
        ADMIN = 2

    user_id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True, blank=False)
    password = models.CharField(max_length=256, null=False)
    user_type = enum.EnumField(USER_TYPE, default=USER_TYPE.USER)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    status = enum.EnumField(USER_STATUS, default=USER_STATUS.ACTIVE)

    def set_password(self, raw_password):
        """Set password using Django's password hashing"""
        self.password = make_password(raw_password)
    
    def check_password(self, raw_password):
        """Check password using Django's password verification"""
        return check_password(raw_password, self.password)
    
    def __str__(self):
        return self.email

class UserActiveSession(models.Model):
    class Meta:
        db_table = "user_active_session"

    user_active_session_id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, related_name="active_sessions")
    access_token = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)
    last_access_datetime = models.DateTimeField(auto_now=True)

class UserSessionDump(models.Model):
    class Meta:
        db_table = "user_session_dump"

    user_session_dump_id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, related_name="session_dumps")
    access_token = models.CharField(max_length=300)
    login_datetime = models.DateTimeField()
    logout_datetime = models.DateTimeField(auto_now_add=True)
    last_access_datetime = models.DateTimeField(auto_now=True)