"""
Модели приложения shops: поставщики (магазины), категории,
товары и настраиваемые характеристики товаров.
"""
from django.conf import settings
from django.db import models


class Shop(models.Model):
    """Магазин (поставщик)."""

    name = models.CharField('Название', max_length=255)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shops',
        verbose_name='Владелец (поставщик)',
    )
    accepts_orders = models.BooleanField(
        'Принимает заказы',
        default=True,
        help_text='Поставщик может включать и отключать приём заказов',
    )
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Магазин'
        verbose_name_plural = 'Магазины'
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class Category(models.Model):
    """Категория товаров, привязанная к магазину."""

    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name='categories',
        verbose_name='Магазин',
    )
    external_id = models.PositiveIntegerField('ID в системе поставщика')
    name = models.CharField('Название', max_length=255)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        constraints = [
            models.UniqueConstraint(
                fields=['shop', 'external_id'],
                name='unique_shop_category',
            ),
        ]
        ordering = ['name']

    def __str__(self) -> str:
        return f'{self.shop.name} — {self.name}'


class Product(models.Model):
    """Товар магазина."""

    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name='Магазин',
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name='Категория',
    )
    external_id = models.PositiveBigIntegerField('Артикул в системе поставщика')
    model = models.CharField(
        'Модель', max_length=255, help_text='Например: apple/iphone/xs-max'
    )
    name = models.CharField('Наименование', max_length=255)
    description = models.TextField('Описание', blank=True, default='')
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2)
    price_rrc = models.DecimalField(
        'Рекомендованная цена (РРЦ)', max_digits=10, decimal_places=2
    )
    quantity = models.PositiveIntegerField('Количество на складе', default=0)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлён', auto_now=True)

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        constraints = [
            models.UniqueConstraint(
                fields=['shop', 'external_id'],
                name='unique_shop_product',
            ),
        ]
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class ProductParameter(models.Model):
    """
    Настраиваемая характеристика товара.
    Позволяет добавлять товару любые поля «имя — значение»
    (диагональ, цвет, память и т.д.) — требование ТЗ.
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='parameters',
        verbose_name='Товар',
    )
    name = models.CharField('Название характеристики', max_length=255)
    value = models.CharField('Значение', max_length=255)

    class Meta:
        verbose_name = 'Характеристика товара'
        verbose_name_plural = 'Характеристики товаров'
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'name'],
                name='unique_product_parameter',
            ),
        ]
        ordering = ['name']

    def __str__(self) -> str:
        return f'{self.name}: {self.value}'