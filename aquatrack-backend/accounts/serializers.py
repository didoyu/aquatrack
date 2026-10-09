from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from monitoring.models import Household

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "phone_number", "role",
              "is_superuser", "date_joined")
        read_only_fields = ("id", "email", "role", "is_superuser", "date_joined")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    household_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    address = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ("email", "password", "first_name", "last_name", "phone_number",
                  "household_name", "address")

    def validate_email(self, value):
        value = value.lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate(self, attrs):
        candidate = User(email=attrs.get("email"), first_name=attrs.get("first_name", ""),
                         last_name=attrs.get("last_name", ""))
        validate_password(attrs["password"], candidate)
        return attrs

    @transaction.atomic
    def create(self, validated):
        household_name = validated.pop("household_name", "") or "My Home"
        address = validated.pop("address", "")
        # Public registration always creates a homeowner (never staff)
        user = User.objects.create_user(role=User.Role.HOMEOWNER, **validated)
        Household.objects.create(owner=user, name=household_name, address=address)
        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_old_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value):
        validate_password(value, self.context["request"].user)
        return value


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Login with email + password (USERNAME_FIELD is email). Also returns the user."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data
