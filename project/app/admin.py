from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Booking,
    BookingItem,
    Genre,
    Hall,
    Movie,
    MovieGenre,
    Review,
    recalculate_movie_rating,
    Seat,
    SeatCategory,
    Session,
    SessionSeatPrice,
    Ticket,
    User,
)

def save_model(self, request, obj, form, change):
    if not change and obj.average_rating and not obj.base_rating:
        obj.base_rating = obj.average_rating
    super().save_model(request, obj, form, change)
    recalculate_movie_rating(obj)


class MovieGenreInline(admin.TabularInline):
    """
    Инлайн-класс для удобного добавления жанров прямо
    на странице редактирования конкретного фильма в админке.
    """

    model = MovieGenre
    extra = 1


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    """Конфигурация панели администратора для управления каталогом фильмов."""

    list_display = (
        "title",
        "release_year",
        "duration_minutes",
        "age_rating",
        "status",
        "average_rating",
    )
    list_filter = ("status", "age_rating", "release_year")
    search_fields = ("title", "description")
    inlines = [MovieGenreInline]


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    """Конфигурация панели администратора для справочника жанров."""

    list_display = ("name", "description")
    search_fields = ("name",)


@admin.register(Hall)
class HallAdmin(admin.ModelAdmin):
    """Конфигурация панели администратора для кинозалов."""

    list_display = ("name", "capacity", "status")
    list_filter = ("status",)


@admin.register(SeatCategory)
class SeatCategoryAdmin(admin.ModelAdmin):
    """Конфигурация панели администратора для категорий мест (Стандарт, VIP и т.д.)."""

    list_display = ("name", "is_active")


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    """Конфигурация панели администратора для мест в залах."""

    list_display = ("hall", "row_number", "seat_number", "category", "is_active")
    list_filter = ("hall", "category", "is_active")


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    """Конфигурация панели администратора для расписания сеансов."""

    list_display = (
        "movie",
        "hall",
        "start_time",
        "format",
        "language",
        "status",
    )
    list_filter = ("status", "format", "start_time")


@admin.register(SessionSeatPrice)
class SessionSeatPriceAdmin(admin.ModelAdmin):
    """Конфигурация панели администратора для ценообразования билетов по сеансам."""

    list_display = ("session", "category", "price", "is_active")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    """Конфигурация панели администратора для заказов (бронирований)."""

    list_display = (
        "booking_code",
        "user",
        "session",
        "status",
        "total_amount",
        "created_at",
    )
    list_filter = ("status", "created_at")


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    """
    Конфигурация панели администратора для электронных билетов.
    Переопределяет методы удаления для каскадной очистки связанных позиций брони.
    """

    list_display = ("id", "booking", "session", "seat", "price", "status")

    def delete_model(self, request, obj):
        """Удаляет связанную позицию брони при удалении билета через админку."""
        if obj.booking_item:
            obj.booking_item.delete()
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        """Массовое удаление связанных позиций брони."""
        for obj in queryset:
            if obj.booking_item:
                obj.booking_item.delete()
        super().delete_queryset(request, queryset)

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("movie", "user", "rating", "moderation_status", "created_at")
    list_filter = ("moderation_status", "rating")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        recalculate_movie_rating(obj.movie)

    def delete_model(self, request, obj):
        movie = obj.movie
        super().delete_model(request, obj)
        recalculate_movie_rating(movie)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Расширенная админ-панель для кастомной модели пользователя (добавлены роли и телефон)."""

    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "is_staff",
    )
    list_filter = ("role", "is_active", "is_staff")
    fieldsets = UserAdmin.fieldsets + (
        ("Дополнительно", {"fields": ("role", "phone")}),
    )
