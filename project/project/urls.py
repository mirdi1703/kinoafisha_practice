from app import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Главная и афиша
    path("", views.movie_list_view, name="movie_list"),
    # Расписание сеансов
    path("schedule/", views.schedule_view, name="schedule"),
    # Детали фильма
    path("movie/<int:pk>/", views.movie_detail_view, name="movie_detail"),
    # Бронирование мест на сеанс
    path("session/<int:pk>/book/", views.session_booking_view, name="session_booking"),
    # Оплата
    path("booking/<int:pk>/pay/", views.payment_view, name="payment_page"),
    # Кассир
    path("cashier/", views.cashier_panel_view, name="cashier_panel"),
    # Авторизация и профиль
    path("profile/", views.profile_view, name="profile"),
    path("register/", views.register_view, name="register"),
    path(
        "login/",
        views.CustomLoginView.as_view(template_name="app/login.html"),
        name="login",
    ),
    path(
        "logout/",
        LogoutView.as_view(next_page="movie_list"),
        name="logout",
    ),
    # Управление отзывами
    path("review/<int:pk>/edit/", views.edit_review_view, name="edit_review"),
    path(
        "review/<int:pk>/delete/",
        views.delete_review_view,
        name="delete_review",
    ),
    # AJAX эндпоинт для проверки занятых мест
    path(
        "api/session/<int:session_id>/seats/",
        views.session_seats_api,
        name="session_seats_api",
    ),

    path("booking/<int:pk>/cancel/", views.cancel_booking_view, name="cancel_booking"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
