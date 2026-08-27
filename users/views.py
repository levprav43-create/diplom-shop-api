"""API-вьюхи приложения users: регистрация, вход, восстановление пароля."""
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.tasks import send_email

from .serializers import LoginSerializer, RegisterSerializer

User = get_user_model()


class RegisterView(APIView):
    """Регистрация нового клиента (доступна без входа)."""

    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token = Token.objects.create(user=user)
        # Письмо через Celery (не блокирует ответ API)
        send_email.delay(
            subject='Регистрация в сервисе заказов — успешно',
            message=(
                f'Здравствуйте, {user.first_name}!\n\n'
                f'Вы успешно зарегистрированы в сервисе заказа товаров.\n'
                f'Ваш логин (email): {user.email}\n\n'
                f'Приятных покупок!'
            ),
            recipient_list=[user.email],
        )
        return Response(
            {'id': user.id, 'email': user.email, 'token': token.key},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """Вход по email и паролю; возвращает токен для дальнейших запросов."""

    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        candidate = User.objects.filter(email__iexact=email).first()
        user = None
        if candidate is not None:
            user = authenticate(
                request, username=candidate.username, password=password
            )

        if user is None:
            return Response(
                {'detail': 'Неверный email или пароль'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'email': user.email, 'token': token.key})


class PasswordResetRequestView(APIView):
    """Восстановление пароля: письмо с uid/token через Celery."""

    permission_classes = (AllowAny,)

    def post(self, request):
        email = (request.data.get('email') or '').lower()
        user = User.objects.filter(email__iexact=email).first()

        if user is not None:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            send_email.delay(
                subject='Восстановление пароля',
                message=(
                    f'Здравствуйте, {user.first_name}!\n\n'
                    f'Получен запрос на восстановление пароля.\n'
                    f'Чтобы задать новый пароль, отправьте запрос на '
                    f'/api/auth/password-reset-confirm/ со следующими данными:\n'
                    f'uid: {uid}\n'
                    f'token: {token}\n\n'
                    f'Если это были не вы — просто проигнорируйте письмо.'
                ),
                recipient_list=[user.email],
            )

        return Response(
            {'detail': 'Если email зарегистрирован, письмо с инструкциями отправлено.'}
        )


class PasswordResetConfirmView(APIView):
    """Устанавливает новый пароль по uid и token из письма."""

    permission_classes = (AllowAny,)

    def post(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token')
        new_password = request.data.get('new_password') or ''

        try:
            pk = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=pk)
        except (TypeError, ValueError, OverflowError, ValidationError, User.DoesNotExist):
            return Response(
                {'detail': 'Неверный или просроченный код восстановления'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not default_token_generator.check_token(user, token):
            return Response(
                {'detail': 'Неверный или просроченный токен восстановления'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(new_password) < 8:
            return Response(
                {'detail': 'Пароль должен быть не короче 8 символов'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save()
        Token.objects.filter(user=user).delete()
        return Response({'detail': 'Пароль изменён. Войдите с новым паролем.'})