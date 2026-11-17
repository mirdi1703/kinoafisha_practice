from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from .forms import ReviewForm, UserRegisterForm
from .models import Booking, Genre, Movie, Review


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