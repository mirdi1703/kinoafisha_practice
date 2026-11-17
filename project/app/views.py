import base64
from datetime import timedelta
from io import BytesIO
import uuid
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
import qrcode
from django.contrib.admin.views.decorators import staff_member_required
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
)


def movie_list_view(request):
  movies = Movie.objects.filter(status='in_poster')
  genres = Genre.objects.all()

  query = request.GET.get('q', '').strip()
  genre_id = request.GET.get('genre', '')

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
      'movies': movies,
      'genres': genres,
      'selected_genre': int(genre_id) if genre_id.isdigit() else '',
      'search_query': query,
  }

  if request.headers.get('x-requested-with') == 'XMLHttpRequest':
    html = render_to_string(
        'app/partials/movies_grid.html', context, request=request
    )
    return JsonResponse({'html': html})

  return render(request, 'app/movie_list.html', context)


def movie_detail_view(request, pk):
  movie = get_object_or_404(Movie, pk=pk)
  sessions = movie.sessions.filter(status='scheduled')
  reviews = movie.reviews.filter(moderation_status='published')
  context = {'movie': movie, 'sessions': sessions, 'reviews': reviews}
  return render(request, 'app/movie_detail.html', context)


@login_required
def profile_view(request):
  bookings = (
      Booking.objects.filter(user=request.user)
      .select_related('session__movie', 'session__hall')
      .prefetch_related('items__seat', 'tickets')
      .order_by('-created_at')
  )
  reviews = (
      Review.objects.filter(user=request.user)
      .select_related('movie')
      .order_by('-created_at')
  )
  context = {
      'bookings': bookings,
      'reviews': reviews,
  }
  return render(request, 'app/profile.html', context)


def register_view(request):
  if request.method == 'POST':
    form = UserRegisterForm(request.POST)
    if form.is_valid():
      user = form.save()
      login(request, user)
      return redirect('movie_list')
  else:
    form = UserRegisterForm()
  return render(request, 'app/register.html', {'form': form})


class CustomLoginView(LoginView):
  template_name = 'app/login.html'

def movie_detail_view(request, pk):
  movie = get_object_or_404(Movie, pk=pk)
  sessions = movie.sessions.filter(status='scheduled')
  reviews = movie.reviews.filter(moderation_status='published')

  user_review = None
  if request.user.is_authenticated:
    user_review = Review.objects.filter(user=request.user, movie=movie).first()

  if request.method == 'POST':
    if not request.user.is_authenticated:
      return redirect('login')

    if user_review:
      messages.warning(request, 'Вы уже оставляли отзыв на этот фильм.')
      return redirect('movie_detail', pk=movie.pk)

    form = ReviewForm(request.POST)
    if form.is_valid():
      review = form.save(commit=False)
      review.user = request.user
      review.movie = movie
      # Если хотите, чтобы отзыв появлялся сразу без ручной проверки в админке,
      # раскомментируйте следующую строку:
      # review.moderation_status = 'published'
      review.save()
      messages.success(
          request, 'Спасибо! Ваш отзыв отправлен на проверку модератору.'
      )
      return redirect('movie_detail', pk=movie.pk)
  else:
    form = ReviewForm()

  context = {
      'movie': movie,
      'sessions': sessions,
      'reviews': reviews,
      'form': form,
      'user_review': user_review,
  }
  return render(request, 'app/movie_detail.html', context)

@login_required
def edit_review_view(request, pk):
  review = get_object_or_404(Review, pk=pk, user=request.user)

  if request.method == 'POST':
    form = ReviewForm(request.POST, instance=review)
    if form.is_valid():
      updated_review = form.save(commit=False)
      updated_review.moderation_status = 'pending'
      updated_review.save()
      messages.success(
          request, 'Отзыв обновлён и отправлен на повторную проверку.'
      )
      return redirect('profile')
  else:
    form = ReviewForm(instance=review)

  context = {
      'form': form,
      'review': review,
  }
  return render(request, 'app/edit_review.html', context)


@login_required
def delete_review_view(request, pk):
  review = get_object_or_404(Review, pk=pk, user=request.user)
  if request.method == 'POST':
    review.delete()
    messages.success(request, 'Ваш отзыв успешно удалён.')
  return redirect('profile')

def schedule_view(request):
  now = timezone.now()
  sessions_qs = (
      Session.objects.filter(start_time__gte=now, status='scheduled')
      .select_related('movie', 'hall')
      .prefetch_related('seat_prices', 'movie__movie_genres__genre')
      .order_by('start_time')
  )

  selected_date = request.GET.get('date', '').strip()
  selected_hall = request.GET.get('hall', '').strip()

  # Список активных залов для фильтра
  halls = Hall.objects.filter(status='active').order_by('name')

  # Доступные даты сеансов для быстрого выбора
  available_dates = sorted(
      {timezone.localtime(s.start_time).date() for s in sessions_qs}
  )

  if selected_date:
    try:
      filter_date = timezone.datetime.strptime(
          selected_date, '%Y-%m-%d'
      ).date()
      sessions_qs = sessions_qs.filter(start_time__date=filter_date)
    except ValueError:
      selected_date = ''

  if selected_hall:
    sessions_qs = sessions_qs.filter(hall_id=selected_hall)
    try:
      selected_hall = int(selected_hall)
    except ValueError:
      selected_hall = ''

  context = {
      'sessions': sessions_qs,
      'halls': halls,
      'available_dates': available_dates,
      'selected_date': selected_date,
      'selected_hall': selected_hall,
  }
  return render(request, 'app/schedule.html', context)

@login_required
def session_booking_view(request, pk):
  session = get_object_or_404(Session, pk=pk)
  seats = (
      Seat.objects.filter(hall=session.hall, is_active=True)
      .select_related('category')
      .order_by('row_number', 'seat_number')
  )

  prices_map = {
      sp.category_id: sp.price
      for sp in SessionSeatPrice.objects.filter(
          session=session, is_active=True
      )
  }

  occupied_seat_ids = set(
      Ticket.objects.filter(
          session=session, status__in=['valid', 'used']
      ).values_list('seat_id', flat=True)
  )

  if request.method == 'POST':
    seat_ids = request.POST.getlist('seats')
    if not seat_ids:
      messages.warning(request, 'Выберите хотя бы одно место в зале.')
      return redirect('session_booking', pk=session.pk)

    with transaction.atomic():
      selected_seats = list(
          Seat.objects.select_for_update()
          .filter(id__in=seat_ids, hall=session.hall, is_active=True)
          .select_related('category')
      )

      # Проверка занятости по актуальным действующим билетам
      already_taken = Ticket.objects.filter(
          session=session,
          seat_id__in=[s.id for s in selected_seats],
          status__in=['valid', 'used'],
      ).exists()

      if already_taken or len(selected_seats) != len(seat_ids):
        messages.warning(
            request, 'Одно или несколько выбранных мест уже заняты.'
        )
        return redirect('session_booking', pk=session.pk)

      total_amount = sum(
          prices_map.get(seat.category_id, 0) for seat in selected_seats
      )
      booking_code = uuid.uuid4().hex[:8].upper()

      booking = Booking.objects.create(
          user=request.user,
          session=session,
          expires_at=timezone.now() + timedelta(minutes=15),
          status='paid',
          total_amount=total_amount,
          booking_code=booking_code,
          seats_count=len(selected_seats),
      )

      for seat in selected_seats:
        seat_price = prices_map.get(seat.category_id, 0)
        item = BookingItem.objects.create(
            booking=booking,
            seat=seat,
            price_at_booking=seat_price,
            status='paid',
        )
        Ticket.objects.create(
            booking=booking,
            booking_item=item,
            session=session,
            seat=seat,
            price=seat_price,
            status='valid',
            qr_code=uuid.uuid4().hex[:16].upper(),
        )

    messages.success(
        request,
        f'Бронь #{booking.booking_code} оформлена! Билеты доступны в личном кабинете.',
    )
    return redirect('profile')

  rows_dict = {}
  for seat in seats:
    rows_dict.setdefault(seat.row_number, []).append({
        'id': seat.id,
        'number': seat.seat_number,
        'category': seat.category.name,
        'price': float(prices_map.get(seat.category_id, 0)),
        'is_occupied': seat.id in occupied_seat_ids,
    })

  rows = sorted(rows_dict.items())

  context = {
      'session': session,
      'rows': rows,
      'seat_prices': SessionSeatPrice.objects.filter(
          session=session, is_active=True
      ).select_related('category'),
  }
  return render(request, 'app/session_booking.html', context)

def movies_view(request):
  now = timezone.now()
  sessions_qs = (
      Session.objects.filter(start_time__gte=now, status='scheduled')
      .select_related('movie', 'hall')
      .prefetch_related('seat_prices', 'movie__movie_genres__genre')
      .order_by('start_time')
  )

  selected_date = request.GET.get('date', '').strip()
  selected_movie = request.GET.get('movie', '').strip()
  selected_format = request.GET.get('format', '').strip()

  available_dates = sorted(
      {timezone.localtime(s.start_time).date() for s in sessions_qs}
  )

  movies_with_sessions = (
      Movie.objects.filter(sessions__in=sessions_qs)
      .distinct()
      .order_by('title')
  )

  if selected_date:
    try:
      filter_date = timezone.datetime.strptime(
          selected_date, '%Y-%m-%d'
      ).date()
      sessions_qs = sessions_qs.filter(start_time__date=filter_date)
    except ValueError:
      selected_date = ''

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
        if getattr(sp, 'is_active', True)
    ]
    session.min_price = min(prices) if prices else None

    grouped_sessions.setdefault(day_key, []).append(session)

  schedule_days = [
      {'date': day, 'sessions': items}
      for day, items in sorted(grouped_sessions.items())
  ]

  context = {
      'schedule_days': schedule_days,
      'available_dates': available_dates,
      'movies_with_sessions': movies_with_sessions,
      'selected_date': selected_date,
      'selected_movie': selected_movie,
      'selected_format': selected_format,
      'total_sessions': sessions_qs.count(),
  }
  return render(request, 'app/movies.html', context)

@login_required
def payment_view(request, pk):
  booking = get_object_or_404(Booking, pk=pk, user=request.user)

  # Проверяем, созданы ли уже билеты для этого заказа
  tickets = booking.tickets.all()

  if request.method == 'POST':
    if not tickets.exists():
      # Создаем билет для каждой позиции брони (`BookingItem`)
      for item in booking.items.all():
        Ticket.objects.create(
            booking=booking,
            booking_item=item,
            session=booking.session,
            seat=item.seat,
            price=item.price,  # берем цену из позиции брони
            status='valid',
            qr_code=uuid.uuid4().hex,  # генерируем уникальный 32-значный токен для QR
        )
      tickets = booking.tickets.all()

    return redirect('payment_page', pk=booking.pk)

  # Генерация картинок QR-кодов в base64 для отображения на странице
  ticket_qrs = []
  for ticket in tickets:
    # Данные зашиваемые в QR-код (например, токен или служебная строка)
    qr_data = f'KINO-TICKET-{ticket.qr_code}-ROW-{ticket.seat.row_number}-SEAT-{ticket.seat.seat_number}'

    img = qrcode.make(qr_data)
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    ticket_qrs.append({'ticket': ticket, 'qr_image': qr_base64})

  context = {
      'booking': booking,
      'ticket_qrs': ticket_qrs,
      'is_paid': tickets.exists(),
  }
  return render(request, 'app/payment.html', context)

@staff_member_required
def cashier_panel_view(request):
  search_query = request.GET.get('q', '').strip()
  ticket = None
  error_message = None
  success_message = None

  if request.method == 'POST':
    action = request.POST.get('action')

    # Погашение билета по QR-токену
    if action == 'verify_ticket':
      code = request.POST.get('qr_code', '').strip()
      try:
        ticket = Ticket.objects.select_related(
            'booking__user', 'session__movie', 'session__hall', 'seat'
        ).get(qr_code=code)

        if ticket.status == 'valid':
          ticket.status = 'used'
          ticket.save()
          success_message = (
              f'Билет #{ticket.id} успешно погашен! Место: Ряд'
              f' {ticket.seat.row_number}, Место {ticket.seat.seat_number}.'
          )
        elif ticket.status == 'used':
          error_message = (
              f'Внимание! Билет #{ticket.id} уже был погашен ранее.'
          )
        else:
          error_message = (
              f'Билет недействителен (статус: {ticket.get_status_display()}).'
          )
      except Ticket.DoesNotExist:
        error_message = 'Билет с таким QR-кодом / токеном не найден в базе.'

    # Быстрый поиск билета по коду или номеру брони
    elif action == 'search_ticket':
      if search_query:
        try:
          ticket = Ticket.objects.select_related(
              'booking', 'session__movie', 'session__hall', 'seat'
          ).get(qr_code__icontains=search_query)
        except Ticket.DoesNotExist:
          error_message = 'Билет не найден.'

  # Ближайшие сеансы для кассира
  now = timezone.now()
  active_sessions = (
      Session.objects.filter(start_time__gte=now, status='scheduled')
      .select_related('movie', 'hall')
      .order_by('start_time')[:10]
  )

  context = {
      'active_sessions': active_sessions,
      'scanned_ticket': ticket,
      'error_message': error_message,
      'success_message': success_message,
      'search_query': search_query,
  }
  return render(request, 'app/cashier_panel.html', context)