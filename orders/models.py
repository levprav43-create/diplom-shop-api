"""
Модели приложения orders: контакты (адреса доставки),
корзина, заказы и состав заказов.
"""
from decimal import Decimal

from django.conf import settings
from django.db import models

from shops.models import Product


class Contact(models.Model):
    """Контактные данные и адрес доставки клиента."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='contacts',
        verbose_name='Пользователь',
    )
    last_name = models.CharField('Фамилия', max_length=100)
    first_name = models.CharField('Имя', max_length=100)
    middle_name = models.CharField('Отчество', max_length=100, blank=True, default='')
    email = models.EmailField('Email')
    phone = models.CharField('Телефон', max_length=20)
    address = models.CharField('Адрес', max_length=255, blank=True, default='')
    city = models.CharField('Город', max_length=100)
    street = models.CharField('Улица', max_length=100)
    house = models.CharField('Дом', max_length=20)
    building = models.CharField('Корпус', max_length=20, blank=True, default='')
    structure = models.CharField('Строение', max_length=20, blank=True, default='')
    apartment = models.CharField('Квартира', max_length=20, blank=True, default='')
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Контакт'
        verbose_name_plural = 'Контакты'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.last_name} {self.first_name} — {self.city}, {self.street}'

    @property
    def full_address(self) -> str:
        """Собирает полный адрес доставки одной строкой."""
        parts = [self.city, self.street, f'д. {self.house}']
        if self.building:
            parts.append(f'корп. {self.building}')
        if self.structure:
            parts.append(f'стр. {self.structure}')
        if self.apartment:
            parts.append(f'кв. {self.apartment}')
        return ', '.join(parts)


class Cart(models.Model):
    """Корзина клиента (одна на пользователя)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart',
        verbose_name='Пользователь',
    )
    created_at = models.DateTimeField('Создана', auto_now_add=True)

    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'

    def __str__(self) -> str:
        return f'Корзина {self.user.username}'

    @property
    def total_amount(self) -> Decimal:
        """Итоговая сумма всех позиций корзины."""
        return sum((item.amount for item in self.items.all()), Decimal('0'))

    @property
    def products_count(self) -> int:
        """Общее количество товаров в корзине."""
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    """Позиция корзины: товар + количество."""

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Корзина',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='cart_items',
        verbose_name='Товар',
    )
    quantity = models.PositiveIntegerField('Количество', default=1)

    class Meta:
        verbose_name = 'Позиция корзины'
        verbose_name_plural = 'Позиции корзины'
        constraints = [
            models.UniqueConstraint(
                fields=['cart', 'product'],
                name='unique_cart_product',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.product.name} x{self.quantity}'

    @property
    def amount(self) -> Decimal:
        """Сумма позиции (цена × количество)."""
        return self.product.price * self.quantity


class Order(models.Model):
    """Заказ клиента."""

    class Status(models.TextChoices):
        NEW = 'new', 'Новый'
        PROCESSING = 'processing', 'В обработке'
        SHIPPED = 'shipped', 'Отправлен'
        COMPLETED = 'completed', 'Завершён'
        CANCELLED = 'cancelled', 'Отменён'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name='Пользователь',
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name='Адрес доставки',
    )
    number = models.PositiveBigIntegerField('Номер заказа', unique=True)
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )
    total_amount = models.DecimalField(
        'Итоговая сумма', max_digits=12, decimal_places=2, default=0
    )
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'Заказ №{self.number} ({self.get_status_display()})'

    def save(self, *args, **kwargs):
        """Новому заказу автоматически присваивается следующий номер."""
        if not self.number:
            last = Order.objects.aggregate(max_number=models.Max('number'))['max_number']
            self.number = (last or 0) + 1
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    """Позиция заказа со снапшотом цены и названия на момент покупки."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Заказ',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='order_items',
        verbose_name='Товар',
    )
    product_name = models.CharField('Название товара', max_length=255)
    price = models.DecimalField('Цена на момент заказа', max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField('Количество')

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'

    def __str__(self) -> str:
        return f'{self.product_name} x{self.quantity}'

    @property
    def amount(self) -> Decimal:
        """Сумма позиции заказа."""
        return self.price * self.quantity