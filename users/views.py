"""API-вьюхи приложения users: регистрация и вход."""
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import LoginSerializer, RegisterSerializer

User = get_user_model()


class RegisterView(APIView):
    """Регистрация нового клиента (доступна без входа)."""

    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        # Сразу выдаём токен, чтобы клиент мог работать с API
        token = Token.objects.create(user=user)
        # Письмо с подтверждением регистрации (критерий этапа 5 ТЗ)
        self._send_welcome_email(user)
        return Response(
            {'id': user.id, 'email': user.email, 'token': token.key},
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def _send_welcome_email(user) -> None:
        """Отправляет письмо с подтверждением регистрации и логином."""
        send_mail(
            subject='Регистрация в сервисе заказов — успешно',
            message=(
                f'Здравствуйте, {user.first_name}!\n\n'
                f'Вы успешно зарегистрированы в сервисе заказа товаров.\n'
                f'Ваш логин (email): {user.email}\n\n'
                f'Приятных покупок!'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )


class LoginView(APIView):
    """Вход по email и паролю; возвращает токен для дальнейших запросов."""

    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        # Ищем пользователя по email (работает и для админа, и для клиентов)
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