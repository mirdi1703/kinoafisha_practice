from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
import uuid


class User(AbstractUser):
  """Кастомная модель пользователя (логин username, пароль)."""

  ROLE_CHOICES = [
      ('viewer', 'Зритель'),
      ('cashier', 'Кассир'),
      ('admin', 'Администратор'),
  ]

  phone = models.CharField(
      max_length=20,
      unique=True,
      blank=True,
      null=True,
      verbose_name='Номер телефона',
  )
  role = models.CharField(
      max_length=20, choices=ROLE_CHOICES, default='viewer', verbose_name='Роль'
  )

  class Meta:
    verbose_name = 'Пользователь'
    verbose_name_plural = 'Пользователи'
    ordering = ['-date_joined']

  def __str__(self):
    return f'{self.username} ({self.get_full_name() or "Без имени"})'


class Movie(models.Model):
  STATUS_CHOICES = [
      ('in_poster', 'В афише'),
      ('hidden', 'Скрыт'),
      ('archived', 'Снят с показа'),
  ]

  title = models.CharField(max_length=255, verbose_name='Название фильма')
  description = models.TextField(verbose_name='Описание')
  duration_minutes = models.PositiveIntegerField(
      verbose_name='Длительность (мин)'
  )
  age_rating = models.CharField(max_length=10, verbose_name='Возрастной рейтинг')

  # Заменяем DateField на PositiveIntegerField для хранения только года (например, 2023)
  release_year = models.PositiveIntegerField(verbose_name='Год релиза')

  poster = models.ImageField(
      upload_to='posters/', blank=True, null=True, verbose_name='Постер'
  )
  status = models.CharField(
      max_length=20,
      choices=STATUS_CHOICES,
      default='in_poster',
      verbose_name='Статус показа',
  )
  average_rating = models.DecimalField(
      max_digits=3,
      decimal_places=2,
      default=0.00,
      verbose_name='Средний рейтинг',
  )

  class Meta:
    verbose_name = 'Фильм'
    verbose_name_plural = 'Фильмы'
    ordering = ['-release_year', 'title']

  def __str__(self):
    return f'{self.title} ({self.release_year})'


class Genre(models.Model):
  name = models.CharField(
      max_length=100, unique=True, verbose_name='Название жанра'
  )
  description = models.TextField(blank=True, null=True, verbose_name='Описание')

  class Meta:
    verbose_name = 'Жанр'
    verbose_name_plural = 'Жанры'
    ordering = ['name']

  def __str__(self):
    return self.name


class MovieGenre(models.Model):
  movie = models.ForeignKey(
      Movie,
      on_delete=models.CASCADE,
      related_name='movie_genres',
      verbose_name='Фильм',
  )
  genre = models.ForeignKey(
      Genre,
      on_delete=models.CASCADE,
      related_name='genre_movies',
      verbose_name='Жанр',
  )
  is_primary = models.BooleanField(
      default=False, verbose_name='Основной жанр'
  )

  class Meta:
    verbose_name = 'Жанр фильма'
    verbose_name_plural = 'Жанры фильмов'
    constraints = [
        models.UniqueConstraint(
            fields=['movie', 'genre'], name='unique_movie_genre'
        )
    ]

  def __str__(self):
    return f'{self.movie.title} — {self.genre.name}'


class Hall(models.Model):
  STATUS_CHOICES = [
      ('active', 'Активен'),
      ('repair', 'На ремонте'),
      ('closed', 'Закрыт'),
  ]

  name = models.CharField(
      max_length=100, unique=True, verbose_name='Название зала'
  )
  capacity = models.PositiveIntegerField(verbose_name='Вместимость')
  layout_config = models.TextField(
      blank=True, null=True, verbose_name='Конфигурация зала (JSON)'
  )
  status = models.CharField(
      max_length=20,
      choices=STATUS_CHOICES,
      default='active',
      verbose_name='Статус зала',
  )

  class Meta:
    verbose_name = 'Зал'
    verbose_name_plural = 'Залы'
    ordering = ['name']

  def __str__(self):
    return self.name


class SeatCategory(models.Model):
  name = models.CharField(
      max_length=50, unique=True, verbose_name='Название категории'
  )
  description = models.TextField(blank=True, null=True, verbose_name='Описание')
  is_active = models.BooleanField(default=True, verbose_name='Активна')

  class Meta:
    verbose_name = 'Категория места'
    verbose_name_plural = 'Категории мест'
    ordering = ['name']

  def __str__(self):
    return self.name


class Seat(models.Model):
  hall = models.ForeignKey(
      Hall, on_delete=models.CASCADE, related_name='seats', verbose_name='Зал'
  )
  category = models.ForeignKey(
      SeatCategory,
      on_delete=models.PROTECT,
      related_name='seats',
      verbose_name='Категория места',
  )
  row_number = models.PositiveIntegerField(verbose_name='Номер ряда')
  seat_number = models.PositiveIntegerField(verbose_name='Номер места')
  is_active = models.BooleanField(default=True, verbose_name='Активно')

  class Meta:
    verbose_name = 'Место в зале'
    verbose_name_plural = 'Места в зале'
    ordering = ['hall', 'row_number', 'seat_number']
    constraints = [
        models.UniqueConstraint(
            fields=['hall', 'row_number', 'seat_number'], name='unique_hall_seat'
        )
    ]

  def __str__(self):
    return f'{self.hall.name}, Ряд {self.row_number}, Место {self.seat_number}'


class Session(models.Model):
  FORMAT_CHOICES = [
      ('2D', '2D'),
      ('3D', '3D'),
      ('IMAX', 'IMAX'),
  ]
  STATUS_CHOICES = [
      ('scheduled', 'Запланирован'),
      ('ongoing', 'Идёт'),
      ('finished', 'Завершён'),
      ('cancelled', 'Отменён'),
  ]

  movie = models.ForeignKey(
      Movie,
      on_delete=models.PROTECT,
      related_name='sessions',
      verbose_name='Фильм',
  )
  hall = models.ForeignKey(
      Hall,
      on_delete=models.PROTECT,
      related_name='sessions',
      verbose_name='Зал',
  )
  start_time = models.DateTimeField(verbose_name='Время начала')
  end_time = models.DateTimeField(verbose_name='Время окончания')
  format = models.CharField(
      max_length=20, choices=FORMAT_CHOICES, default='2D', verbose_name='Формат'
  )
  language = models.CharField(
      max_length=50, default='Русский', verbose_name='Язык / Озвучка'
  )
  status = models.CharField(
      max_length=20,
      choices=STATUS_CHOICES,
      default='scheduled',
      verbose_name='Статус сеанса',
  )

  class Meta:
    verbose_name = 'Сеанс'
    verbose_name_plural = 'Сеансы'
    ordering = ['start_time']

  def __str__(self):
    return f'{self.movie.title} ({self.format}) — {self.start_time.strftime("%d-%m-%Y %H:%M")}'


class SessionSeatPrice(models.Model):
  session = models.ForeignKey(
      Session,
      on_delete=models.CASCADE,
      related_name='seat_prices',
      verbose_name='Сеанс',
  )
  category = models.ForeignKey(
      SeatCategory,
      on_delete=models.PROTECT,
      related_name='session_prices',
      verbose_name='Категория места',
  )
  price = models.DecimalField(
      max_digits=10, decimal_places=2, verbose_name='Стоимость (руб.)'
  )
  is_active = models.BooleanField(default=True, verbose_name='Активен')

  class Meta:
    verbose_name = 'Цена по категории места'
    verbose_name_plural = 'Цены по категориям мест'
    constraints = [
        models.UniqueConstraint(
            fields=['session', 'category'], name='unique_session_category_price'
        )
    ]

  def __str__(self):
    return (
        f'Сеанс #{self.session_id} | {self.category.name}: {self.price} руб.'
    )


class Booking(models.Model):
  STATUS_CHOICES = [
      ('active', 'Активна (ожидает оплаты)'),
      ('paid', 'Оплачена'),
      ('cancelled', 'Отменена'),
      ('expired', 'Истекла по таймеру'),
  ]

  user = models.ForeignKey(
      User,
      on_delete=models.PROTECT,
      related_name='bookings',
      verbose_name='Клиент',
  )
  session = models.ForeignKey(
      Session,
      on_delete=models.PROTECT,
      related_name='bookings',
      verbose_name='Сеанс',
  )
  created_at = models.DateTimeField(
      auto_now_add=True, verbose_name='Дата создания'
  )
  expires_at = models.DateTimeField(verbose_name='Срок действия брони')
  status = models.CharField(
      max_length=20,
      choices=STATUS_CHOICES,
      default='active',
      verbose_name='Статус брони',
  )
  total_amount = models.DecimalField(
      max_digits=10, decimal_places=2, verbose_name='Общая сумма'
  )
  booking_code = models.CharField(
      max_length=12, unique=True, verbose_name='Код брони'
  )
  seats_count = models.PositiveIntegerField(verbose_name='Количество мест')

  class Meta:
    verbose_name = 'Бронь'
    verbose_name_plural = 'Брони'
    ordering = ['-created_at']

  def __str__(self):
    return f'Бронь #{self.booking_code} ({self.status})'


class BookingItem(models.Model):
  STATUS_CHOICES = [
      ('reserved', 'Зарезервировано'),
      ('paid', 'Оплачено'),
      ('cancelled', 'Отменено'),
  ]

  booking = models.ForeignKey(
      Booking,
      on_delete=models.CASCADE,
      related_name='items',
      verbose_name='Бронь',
  )
  seat = models.ForeignKey(
      Seat,
      on_delete=models.PROTECT,
      related_name='booking_items',
      verbose_name='Место',
  )
  price_at_booking = models.DecimalField(
      max_digits=10, decimal_places=2, verbose_name='Цена на момент брони'
  )
  status = models.CharField(
      max_length=20,
      choices=STATUS_CHOICES,
      default='reserved',
      verbose_name='Статус позиции',
  )

  class Meta:
    verbose_name = 'Позиция брони'
    verbose_name_plural = 'Позиции брони'
    constraints = [
        models.UniqueConstraint(
            fields=['booking', 'seat'], name='unique_booking_seat'
        )
    ]

  def __str__(self):
    return f'Бронь {self.booking.booking_code} — Место {self.seat}'


class Ticket(models.Model):
  STATUS_CHOICES = [
      ('valid', 'Действителен'),
      ('used', 'Погашен'),
      ('refunded', 'Возвращен'),
      ('cancelled', 'Отменен'),
  ]

  booking = models.ForeignKey(
      Booking,
      on_delete=models.PROTECT,
      related_name='tickets',
      verbose_name='Бронь',
  )
  booking_item = models.OneToOneField(
        BookingItem,
        on_delete=models.CASCADE,  # Изменили с PROTECT на CASCADE
        related_name='ticket',
        verbose_name='Позиция брони',
    )
  session = models.ForeignKey(
      Session,
      on_delete=models.PROTECT,
      related_name='tickets',
      verbose_name='Сеанс',
  )
  seat = models.ForeignKey(
      Seat,
      on_delete=models.PROTECT,
      related_name='tickets',
      verbose_name='Место',
  )
  price = models.DecimalField(
      max_digits=10, decimal_places=2, verbose_name='Цена билета'
  )
  status = models.CharField(
      max_length=20,
      choices=STATUS_CHOICES,
      default='valid',
      verbose_name='Статус билета',
  )
  qr_code = models.CharField(
      max_length=64, unique=True, verbose_name='QR-код / Токен'
  )
  issued_at = models.DateTimeField(
      auto_now_add=True, verbose_name='Дата выпуска'
  )

  class Meta:
    verbose_name = 'Билет'
    verbose_name_plural = 'Билеты'
    ordering = ['-issued_at']

  def __str__(self):
    return f'Билет #{self.id} (Место {self.seat})'


class Review(models.Model):
  MODERATION_CHOICES = [
      ('pending', 'На проверке'),
      ('published', 'Опубликован'),
      ('rejected', 'Отклонён'),
  ]

  user = models.ForeignKey(
      User,
      on_delete=models.CASCADE,
      related_name='reviews',
      verbose_name='Пользователь',
  )
  movie = models.ForeignKey(
      Movie,
      on_delete=models.CASCADE,
      related_name='reviews',
      verbose_name='Фильм',
  )
  rating = models.PositiveIntegerField(
      validators=[MinValueValidator(1), MaxValueValidator(10)],
      verbose_name='Оценка (от 1 до 10)',
  )
  text = models.TextField(verbose_name='Текст отзыва')
  created_at = models.DateTimeField(
      auto_now_add=True, verbose_name='Дата создания'
  )
  moderation_status = models.CharField(
      max_length=20,
      choices=MODERATION_CHOICES,
      default='pending',
      verbose_name='Статус модерации',
  )

  class Meta:
    verbose_name = 'Отзыв'
    verbose_name_plural = 'Отзывы'
    ordering = ['-created_at']
    constraints = [
        models.UniqueConstraint(
            fields=['user', 'movie'], name='unique_user_movie_review'
        )
    ]

def __str__(self):
    return (
        f'Отзыв от {self.user.username} на {self.movie.title} ({self.rating}/10)'
    )