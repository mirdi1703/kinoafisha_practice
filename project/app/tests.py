from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    Booking,
    BookingItem,
    Hall,
    Movie,
    Review,
    Seat,
    SeatCategory,
    Session,
    SessionSeatPrice,
    Ticket,
    User,
    recalculate_movie_rating,
)


class NegativeExceptionHandlingTests(TestCase):
    """5 негативных тестов для проверки обработки исключительных ситуаций."""

    def setUp(self):
        self.viewer = User.objects.create_user(
            username="viewer_test",
            email="viewer@example.ru",
            password="StrongPassword123!",
            first_name="Пётр",
            role="viewer",
        )
        self.movie = Movie.objects.create(
            title="Интерстеллар",
            description="Фантастический фильм о путешествии сквозь червоточину.",
            duration_minutes=169,
            age_rating="12+",
            release_year=2014,
            base_rating=Decimal("8.50"),
        )
        self.hall = Hall.objects.create(name="Зал №1", capacity=50)
        self.category = SeatCategory.objects.create(name="Стандарт")
        self.seat = Seat.objects.create(
            hall=self.hall, category=self.category, row_number=1, seat_number=1
        )
        self.session = Session.objects.create(
            movie=self.movie,
            hall=self.hall,
            start_time=timezone.now() + timedelta(hours=3),
            end_time=timezone.now() + timedelta(hours=6),
            format="IMAX",
        )
        SessionSeatPrice.objects.create(
            session=self.session, category=self.category, price=Decimal("450.00")
        )

    def test_1_nonexistent_record_returns_404(self):
        """1. Обращение к несуществующей записи возвращает 404."""
        response = self.client.get(reverse("movie_detail", kwargs={"pk": 999999}))
        self.assertEqual(response.status_code, 404)

    def test_2_access_without_permissions_returns_403(self):
        """2. Доступ без прав в панель кассира возвращает 403."""
        self.client.force_login(self.viewer)
        response = self.client.get(reverse("cashier_panel"))
        self.assertEqual(response.status_code, 403)

    def test_3_invalid_form_does_not_create_record_and_shows_message(self):
        """3. Форма с неверными данными не создаёт запись и показывает сообщение."""
        self.client.force_login(self.viewer)
        url = reverse("movie_detail", kwargs={"pk": self.movie.pk})
        
        response = self.client.post(url, data={"rating": 9, "text": "Норм"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Review.objects.count(), 0)
        self.assertContains(response, "Слишком короткий отзыв")
        self.assertContains(response, "Норм")

    def test_4_rollback_on_error_in_middle_of_transaction(self):
        """4. При ошибке в середине операции данные не меняются."""
        booking = Booking.objects.create(
            user=self.viewer,
            session=self.session,
            expires_at=timezone.now() + timedelta(minutes=15),
            status="pending",
            total_amount=Decimal("450.00"),
            booking_code="TEST1234",
            seats_count=1,
        )
        BookingItem.objects.create(
            booking=booking,
            seat=self.seat,
            price_at_booking=Decimal("450.00"),
            status="reserved",
        )

        self.client.force_login(self.viewer)
        pay_url = reverse("payment_page", kwargs={"pk": booking.pk})

        with patch(
            "app.views.Ticket.objects.get_or_create",
            side_effect=RuntimeError("Simulated DB crash mid-transaction"),
        ):
            response = self.client.post(pay_url)

        booking.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(booking.status, "pending")
        self.assertEqual(Ticket.objects.count(), 0)

    def test_5_calculation_on_empty_queryset_does_not_crash(self):
        """5. Расчёт на пустой выборке не падает."""
        recalculate_movie_rating(self.movie)
        self.movie.refresh_from_db()
        self.assertEqual(self.movie.average_rating, Decimal("8.50"))

        SessionSeatPrice.objects.all().delete()
        response = self.client.get(reverse("movie_detail", kwargs={"pk": self.movie.pk}))
        self.assertEqual(response.status_code, 200)