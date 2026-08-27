"""Сериализаторы приложения users: регистрация и вход."""
from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    """Данные регистрации по спецификации: фамилия, имя, email, пароль."""

    last_name = serializers.CharField(max_length=100)
    first_name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value):
        """Email должен быть уникальным."""
        email = value.lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                'Пользователь с таким email уже зарегистрирован'
            )
        return email

    def create(self, validated_data):
        """Создаёт пользователя; username = email (вход по email, как в ТЗ)."""
        return User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
        )


class LoginSerializer(serializers.Serializer):
    """Данные входа: email и пароль."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)