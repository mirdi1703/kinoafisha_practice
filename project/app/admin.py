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
    Seat,
    SeatCategory,
    Session,
    SessionSeatPrice,
    Ticket,
    User,
)


class MovieGenreInline(admin.TabularInline):
  model = MovieGenre
  extra = 1


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
  list_display = (
      'title',
      'release_year',
      'duration_minutes',
      'age_rating',
      'status',
      'average_rating',
  )
  list_filter = ('status', 'age_rating', 'release_year')
  search_fields = ('title', 'description')
  inlines = [MovieGenreInline]


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
  list_display = ('name', 'description')
  search_fields = ('name',)


@admin.register(Hall)
class HallAdmin(admin.ModelAdmin):
  list_display = ('name', 'capacity', 'status')
  list_filter = ('status',)


@admin.register(SeatCategory)
class SeatCategoryAdmin(admin.ModelAdmin):
  list_display = ('name', 'is_active')


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
  list_display = ('hall', 'row_number', 'seat_number', 'category', 'is_active')
  list_filter = ('hall', 'category', 'is_active')


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
  list_display = (
      'movie',
      'hall',
      'start_time',
      'format',
      'language',
      'status',
  )
  list_filter = ('status', 'format', 'start_time')


@admin.register(SessionSeatPrice)
class SessionSeatPriceAdmin(admin.ModelAdmin):
  list_display = ('session', 'category', 'price', 'is_active')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
  list_display = (
      'booking_code',
      'user',
      'session',
      'status',
      'total_amount',
      'created_at',
  )
  list_filter = ('status', 'created_at')


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
  list_display = ('id', 'booking', 'session', 'seat', 'price', 'status')

  def delete_model(self, request, obj):
    # При удалении билета админом проверяем, нужно ли удалить связанный BookingItem или освободить бронь
    if obj.booking_item:
      # Если нужно полностью стирать позицию брони при удалении билета:
      obj.booking_item.delete()
    super().delete_model(request, obj)

  def delete_queryset(self, request, queryset):
    for obj in queryset:
      if obj.booking_item:
        obj.booking_item.delete()
    super().delete_queryset(request, queryset)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
  list_display = ('movie', 'user', 'rating', 'moderation_status', 'created_at')
  list_filter = ('moderation_status', 'rating')


@admin.register(User)
class CustomUserAdmin(UserAdmin):
  list_display = (
      'username',
      'email',
      'first_name',
      'last_name',
      'role',
      'is_staff',
  )
  list_filter = ('role', 'is_active', 'is_staff')
  fieldsets = UserAdmin.fieldsets + (('Дополнительно', {'fields': ('role', 'phone')}),)