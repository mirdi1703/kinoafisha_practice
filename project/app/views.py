import base64
from datetime import timedelta
from io import BytesIO
import uuid

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
import qrcode

from .forms import ReviewForm, UserRegisterForm
from .models import (
    Booking,
    BookingItem,
    Genre,
    Hall,
    Movie,
    Review,
    Seat,
    Session,
    SessionSeatPrice,
    Ticket,
    recalculate_movie_rating,
)

import logging
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError, transaction

logger = logging.getLogger("app")

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 600


def _get_client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def _attempt_cache_key(request, username=""):
    ip = _get_client_ip(request)
    user_part = (username or "").strip().lower()
    return f"login_attempts:{ip}:{user_part}"


def movie_list_view(request):
    """
    Представление главной страницы со списком фильмов и каталогом.
    Реализует поиск по названию/описанию, фильтрацию по жанрам
    и поддержку AJAX-запросов для «живого» обновления сетки фильмов.
    """
    movies = Movie.objects.filter(status="in_poster")
    genres = Genre.objects.all()

    query = request.GET.get("q", "").strip()
    genre_id = request.GET.get("genre", "")

    if genre_id:
        movies = movies.filter(movie_genres__genre_id=genre_id).distinct()

    if query:
        q_lower = query.casefold()
        movies = [
            movie
            for movie in movies
            if q_lower in movie.title.casefold()
            or q_lower in movie.description.casefold()
        ]

    context = {
        "movies": movies,
        "genres": genres,
        "selected_genre": int(genre_id) if genre_id.isdigit() else "",
        "search_query": query,
    }

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        html = render_to_string(
            "app/partials/movies_grid.html", context, request=request
        )
        return JsonResponse({"html": html})

    return render(request, "app/movie_list.html", context)


@login_required
def profile_view(request):
    """
    Представление личного кабинета пользователя.
    Загружает историю бронирований и список отзывов текущего пользователя.
    """
    user_bookings_qs = Booking.objects.filter(user=request.user)

    for booking in user_bookings_qs.filter(status__in=["pending", "active"]):
        if booking.is_expired():
            booking.status = "expired"
            booking.save(update_fields=["status"])

    bookings = (
        user_bookings_qs.select_related("session__movie", "session__hall")
        .prefetch_related("items__seat", "tickets", "items")
        .order_by("-created_at")
    )
    reviews = (
        Review.objects.filter(user=request.user)
        .select_related("movie")
        .order_by("-created_at")
    )
    context = {
        "bookings": bookings,
        "reviews": reviews,
    }
    return render(request, "app/profile.html", context)


def register_view(request):
    """
    Представление регистрации нового пользователя.
    При успешном заполнении формы автоматически авторизует его и перенаправляет на главную.
    """
    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("movie_list")
    else:
        form = UserRegisterForm()
    return render(request, "app/register.html", {"form": form})


class RateLimitedLoginView(LoginView):
    """Вход в систему с ограничением числа неудачных попыток."""

    template_name = "app/login.html"

    def _is_blocked(self, request, username=""):
        key_user = _attempt_cache_key(request, username)
        key_ip = _attempt_cache_key(request, "")
        return max(cache.get(key_user, 0), cache.get(key_ip, 0)) >= MAX_LOGIN_ATTEMPTS

    def dispatch(self, request, *args, **kwargs):
        if request.method == "POST":
            username = request.POST.get("username", "")
            if self._is_blocked(request, username):
                messages.error(
                    request,
                    "Слишком много неудачных попыток входа. Повторите через 10 минут.",
                )
                form = self.get_form()
                return self.render_to_response(self.get_context_data(form=form))
        return super().dispatch(request, *args, **kwargs)

    def form_invalid(self, form):
        username = (
            form.cleaned_data.get("username")
            or self.request.POST.get("username", "")
        )
        key_user = _attempt_cache_key(self.request, username)
        key_ip = _attempt_cache_key(self.request, "")

        attempts_user = cache.get(key_user, 0) + 1
        attempts_ip = cache.get(key_ip, 0) + 1
        cache.set(key_user, attempts_user, timeout=LOCKOUT_SECONDS)
        cache.set(key_ip, attempts_ip, timeout=LOCKOUT_SECONDS)

        current_attempts = max(attempts_user, attempts_ip)
        if current_attempts >= MAX_LOGIN_ATTEMPTS:
            messages.error(
                self.request,
                "Превышен лимит попыток входа. Вход временно заблокирован на 10 минут.",
            )
        else:
            remaining = MAX_LOGIN_ATTEMPTS - current_attempts
            messages.warning(
                self.request,
                f"Неверный логин или пароль. Осталось попыток: {remaining}.",
            )
        return super().form_invalid(form)

    def form_valid(self, form):
        username = form.get_user().get_username()
        cache.delete(_attempt_cache_key(self.request, username))
        cache.delete(_attempt_cache_key(self.request, ""))
        return super().form_valid(form)


CustomLoginView = RateLimitedLoginView


def movie_detail_view(request, pk):
    """
    Расширенное представление детальной страницы фильма (с обработкой отзывов).
    Позволяет авторизованному пользователю отправить отзыв с оценкой от 1 до 10.
    """
    movie = get_object_or_404(Movie, pk=pk)
    sessions = movie.sessions.filter(status="scheduled")
    reviews = movie.reviews.filter(moderation_status="published")

    user_review = None
    if request.user.is_authenticated:
        user_review = Review.objects.filter(user=request.user, movie=movie).first()

    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect("login")

        if user_review:
            messages.warning(request, "Вы уже оставляли отзыв на этот фильм.")
            return redirect("movie_detail", pk=movie.pk)

        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.movie = movie
            review.save()
            messages.success(
                request, "Спасибо! Ваш отзыв отправлен на проверку модератору."
            )
            return redirect("movie_detail", pk=movie.pk)
    else:
        form = ReviewForm()

    context = {
        "movie": movie,
        "sessions": sessions,
        "reviews": reviews,
        "form": form,
        "user_review": user_review,
    }
    return render(request, "app/movie_detail.html", context)


@login_required
def edit_review_view(request, pk):
    """
    Представление для редактирования отзыва пользователя.
    После изменения переводит статус отзыва обратно на модерацию ('pending').
    """

    review = get_object_or_404(Review, pk=pk)
    if review.user != request.user:
        logger.warning("Попытка доступа к чужому отзыву #%s пользователем %s", pk, request.user.username)
        raise PermissionDenied("Вы можете управлять только собственными отзывами.")

    if request.method == "POST":
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            updated_review = form.save(commit=False)
            updated_review.moderation_status = "pending"
            updated_review.save()
            messages.success(
                request, "Отзыв обновлён и отправлен на повторную проверку."
            )
            return redirect("profile")
    else:
        form = ReviewForm(instance=review)

    context = {
        "form": form,
        "review": review,
    }
    return render(request, "app/edit_review.html", context)


@login_required
def delete_review_view(request, pk):
    """Представление для удаления отзыва пользователя."""
    review = get_object_or_404(Review, pk=pk, user=request.user)
    if request.method == "POST":
        movie = review.movie
        review.delete()
        recalculate_movie_rating(movie)
        messages.success(request, "Ваш отзыв успешно удалён.")
    return redirect("profile")


def schedule_view(request):
    """
    Представление расписания сеансов.
    Обеспечивает фильтрацию сеансов по дате и кинозалу.
    """
    now = timezone.now()
    sessions_qs = (
        Session.objects.filter(start_time__gte=now, status="scheduled")
        .select_related("movie", "hall")
        .prefetch_related("seat_prices", "movie__movie_genres__genre")
        .order_by("start_time")
    )

    selected_date = request.GET.get("date", "").strip()
    selected_hall = request.GET.get("hall", "").strip()

    halls = Hall.objects.filter(status="active").order_by("name")
    available_dates = sorted(
        {timezone.localtime(s.start_time).date() for s in sessions_qs}
    )

    if selected_date:
        try:
            filter_date = timezone.datetime.strptime(selected_date, "%Y-%m-%d").date()
            sessions_qs = sessions_qs.filter(start_time__date=filter_date)
        except ValueError:
            selected_date = ""

    if selected_hall:
        sessions_qs = sessions_qs.filter(hall_id=selected_hall)
        try:
            selected_hall = int(selected_hall)
        except ValueError:
            selected_hall = ""

    context = {
        "sessions": sessions_qs,
        "halls": halls,
        "available_dates": available_dates,
        "selected_date": selected_date,
        "selected_hall": selected_hall,
    }
    return render(request, "app/schedule.html", context)


def movies_view(request):
    """
    Альтернативное представление расписания с группировкой сеансов по дням и фильмам.
    """
    now = timezone.now()
    sessions_qs = (
        Session.objects.filter(start_time__gte=now, status="scheduled")
        .select_related("movie", "hall")
        .prefetch_related("seat_prices", "movie__movie_genres__genre")
        .order_by("start_time")
    )

    selected_date = request.GET.get("date", "").strip()
    selected_movie = request.GET.get("movie", "").strip()
    selected_format = request.GET.get("format", "").strip()

    available_dates = sorted(
        {timezone.localtime(s.start_time).date() for s in sessions_qs}
    )

    movies_with_sessions = (
        Movie.objects.filter(sessions__in=sessions_qs).distinct().order_by("title")
    )

    if selected_date:
        try:
            filter_date = timezone.datetime.strptime(selected_date, "%Y-%m-%d").date()
            sessions_qs = sessions_qs.filter(start_time__date=filter_date)
        except ValueError:
            selected_date = ""

    if selected_movie:
        sessions_qs = sessions_qs.filter(movie_id=selected_movie)

    if selected_format:
        sessions_qs = sessions_qs.filter(format=selected_format)

    grouped_sessions = {}
    for session in sessions_qs:
        local_dt = timezone.localtime(session.start_time)
        day_key = local_dt.date()

        prices = [
            sp.price
            for sp in session.seat_prices.all()
            if getattr(sp, "is_active", True)
        ]
        session.min_price = min(prices) if prices else None

        grouped_sessions.setdefault(day_key, []).append(session)

    schedule_days = [
        {"date": day, "sessions": items}
        for day, items in sorted(grouped_sessions.items())
    ]

    context = {
        "schedule_days": schedule_days,
        "available_dates": available_dates,
        "movies_with_sessions": movies_with_sessions,
        "selected_date": selected_date,
        "selected_movie": selected_movie,
        "selected_format": selected_format,
        "total_sessions": sessions_qs.count(),
    }
    return render(request, "app/movies.html", context)


@login_required
def cashier_panel_view(request):
    """
    Панель кассира (доступна только персоналу).
    Позволяет проверять и гасить билеты по уникальному QR-коду / токену,
    а также осуществлять поиск билетов.
    """

    if not (request.user.is_staff or getattr(request.user, "role", "") in ("cashier", "admin")):
        logger.warning(
            "Доступ запрещён в панель кассира: user=%s, path=%s",
            request.user.username,
            request.path,
        )
        raise PermissionDenied("Доступ в панель кассира разрешён только сотрудникам.")

    search_query = request.GET.get("q", "").strip()
    ticket = None
    error_message = None
    success_message = None

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "verify_ticket":
            code = request.POST.get("qr_code", "").strip()
            try:
                ticket = Ticket.objects.select_related(
                    "booking__user", "session__movie", "session__hall", "seat"
                ).get(qr_code=code)

                if ticket.status == "valid":
                    ticket.status = "used"
                    ticket.save()
                    success_message = (
                        f"Билет #{ticket.id} успешно погашен! Место: Ряд"
                        f" {ticket.seat.row_number}, Место {ticket.seat.seat_number}."
                    )
                elif ticket.status == "used":
                    error_message = (
                        f"Внимание! Билет #{ticket.id} уже был погашен ранее."
                    )
                else:
                    error_message = (
                        f"Билет недействителен (статус: {ticket.get_status_display()})."
                    )
            except Ticket.DoesNotExist:
                error_message = "Билет с таким QR-кодом / токеном не найден в базе."

        elif action == "search_ticket":
            if search_query:
                try:
                    ticket = Ticket.objects.select_related(
                        "booking", "session__movie", "session__hall", "seat"
                    ).get(qr_code__icontains=search_query)
                except Ticket.DoesNotExist:
                    error_message = "Билет не найден."

    now = timezone.now()
    active_sessions = (
        Session.objects.filter(start_time__gte=now, status="scheduled")
        .select_related("movie", "hall")
        .order_by("start_time")[:10]
    )

    context = {
        "active_sessions": active_sessions,
        "scanned_ticket": ticket,
        "error_message": error_message,
        "success_message": success_message,
        "search_query": search_query,
    }
    return render(request, "app/cashier_panel.html", context)


def session_seats_api(request, session_id):
    """
    API-эндпоинт для получения занятых мест на сеансе без перезагрузки (AJAX).
    Автоматически переводит просроченные брони (>15 минут) в статус 'expired'
    и возвращает JSON со списком ID занятых мест.
    """
    session = get_object_or_404(Session, pk=session_id)

    pending_bookings = Booking.objects.filter(session=session, status="pending")
    for booking in pending_bookings:
        if booking.is_expired():
            booking.status = "expired"
            booking.save()

    active_bookings = Booking.objects.filter(
        session=session, status__in=["pending", "paid"]
    )
    occupied_seat_ids = list(
        BookingItem.objects.filter(booking__in=active_bookings).values_list(
            "seat_id", flat=True
        )
    )

    return JsonResponse({"occupied_seats": occupied_seat_ids})


@login_required
def session_booking_view(request, pk):
    """
    Представление интерактивной схемы зала и бронирования мест.
    Использует транзакции (`transaction.atomic`) и блокировку строк (`select_for_update`)
    для предотвращения одновременного бронирования (гонки потоков).
    Создает бронь со статусом 'pending' на 15 минут.
    """
    session = get_object_or_404(Session, pk=pk)
    seats = (
        Seat.objects.filter(hall=session.hall, is_active=True)
        .select_related("category")
        .order_by("row_number", "seat_number")
    )

    prices_map = {
        sp.category_id: sp.price
        for sp in SessionSeatPrice.objects.filter(session=session, is_active=True)
    }

    pending_bookings = Booking.objects.filter(session=session, status="pending")
    for b in pending_bookings:
        if b.is_expired():
            b.status = "expired"
            b.save()

    active_bookings = Booking.objects.filter(
        session=session, status__in=["pending", "paid"]
    )
    occupied_seat_ids = set(
        BookingItem.objects.filter(booking__in=active_bookings).values_list(
            "seat_id", flat=True
        )
    )

    if request.method == "POST":
        seat_ids = request.POST.getlist("seats")
        if not seat_ids:
            messages.warning(request, "Выберите хотя бы одно место в зале.")
            return redirect("session_booking", pk=session.pk)

        with transaction.atomic():
            active_items = BookingItem.objects.select_for_update().filter(
                booking__session=session,
                booking__status__in=["pending", "paid"],
                seat_id__in=seat_ids,
            )

            if active_items.exists():
                messages.warning(
                    request,
                    "Кто-то только что занял выбранные вами места. Пожалуйста, выберите другие.",
                )
                return redirect("session_booking", pk=session.pk)

            total_amount = sum(
                prices_map.get(Seat.objects.get(pk=s_id).category_id, 0)
                for s_id in seat_ids
            )
            booking_code = uuid.uuid4().hex[:8].upper()

            booking = Booking.objects.create(
                user=request.user,
                session=session,
                expires_at=timezone.now() + timedelta(minutes=15),
                status="pending",
                total_amount=total_amount,
                booking_code=booking_code,
                seats_count=len(seat_ids),
            )

            for seat_id in seat_ids:
                seat = Seat.objects.get(pk=seat_id)
                seat_price = prices_map.get(seat.category_id, 0)
                BookingItem.objects.create(
                    booking=booking,
                    seat=seat,
                    price_at_booking=seat_price,
                    status="reserved",
                )

        messages.success(
            request,
            f"Места забронированы! У вас есть 15 минут на оплату заказа #{booking.booking_code}.",
        )
        return redirect("payment_page", pk=booking.pk)

    rows_dict = {}
    for seat in seats:
        rows_dict.setdefault(seat.row_number, []).append(
            {
                "id": seat.id,
                "number": seat.seat_number,
                "category": seat.category.name,
                "price": float(prices_map.get(seat.category_id, 0)),
                "is_occupied": seat.id in occupied_seat_ids,
            }
        )

    rows = sorted(rows_dict.items())

    context = {
        "session": session,
        "rows": rows,
        "seat_prices": SessionSeatPrice.objects.filter(
            session=session, is_active=True
        ).select_related("category"),
    }
    return render(request, "app/session_booking.html", context)


@login_required
def payment_view(request, pk):
    """
    Представление страницы оплаты заказа и генерации билетов с QR-кодами.
    Проверяет 15-минутный таймер брони. При подтверждении оплаты переводит заказ
    в статус 'paid', формирует билеты и генерирует для них изображения QR-кодов.
    """
    booking = get_object_or_404(Booking, pk=pk, user=request.user)

    if booking.status == "pending" and booking.is_expired():
        booking.status = "expired"
        booking.save()
        messages.error(
            request, "Время брони истекло (прошло более 15 минут). Места освобождены."
        )
        return redirect("profile")

    if booking.status == "expired" or booking.status == "cancelled":
        messages.error(request, "Эта бронь просрочена или отменена.")
        return redirect("profile")

    if request.method == "POST":
        try:
            with transaction.atomic():
                booking.status = "paid"
                booking.save(update_fields=["status"])

                for item in booking.items.all():
                    Ticket.objects.get_or_create(
                        booking=booking,
                        booking_item=item,
                        defaults={
                            "session": booking.session,
                            "seat": item.seat,
                            "price": item.price_at_booking,
                            "status": "valid",
                            "qr_code": uuid.uuid4().hex[:16].upper(),
                        },
                    )
        except Exception:
            logger.exception("Сбой транзакции при оплате брони #%s", booking.pk)
            messages.error(
                request,
                "Произошла ошибка при оформлении билетов. Средства не списаны, попробуйте ещё раз.",
            )
            return redirect("payment_page", pk=booking.pk)

        messages.success(request, "Оплата прошла успешно! Билеты оформлены.")
        return redirect("payment_page", pk=booking.pk)

    tickets = booking.tickets.all()
    ticket_qrs = []

    if booking.status == "paid":
        for ticket in tickets:
            qr_data = f"KINO-TICKET-{ticket.qr_code}-ROW-{ticket.seat.row_number}-SEAT-{ticket.seat.seat_number}"
            img = qrcode.make(qr_data)
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
            ticket_qrs.append({"ticket": ticket, "qr_image": qr_base64})

    context = {
        "booking": booking,
        "ticket_qrs": ticket_qrs,
        "is_paid": booking.status == "paid",
    }
    return render(request, "app/payment.html", context)


@login_required
def cancel_booking_view(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if booking.user != request.user:
        logger.warning("Попытка доступа к чужой брони #%s пользователем %s", pk, request.user.username)
        raise PermissionDenied("Эта бронь принадлежит другому пользователю.")
    if request.method == "POST" and booking.status in ["pending", "active"]:
        with transaction.atomic():
            booking.status = "cancelled"
            booking.save(update_fields=["status"])
            booking.items.filter(status="reserved").update(status="cancelled")
        messages.success(
            request,
            f"Бронь #{booking.booking_code or booking.id} отменена, места освобождены.",
        )
    return redirect("profile")