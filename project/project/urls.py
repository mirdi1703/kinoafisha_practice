from app import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.movie_list_view, name='movie_list'),
    path('movies/', views.movie_list_view, name='movies'),
    path('movie/<int:pk>/', views.movie_detail_view, name='movie_detail'),
    path('profile/', views.profile_view, name='profile'),
    path('register/', views.register_view, name='register'),
    path(
        'login/',
        views.CustomLoginView.as_view(template_name='app/login.html'),
        name='login',
    ),
    path(
        'logout/',
        LogoutView.as_view(next_page='movie_list'),
        name='logout',
    ),
]

if settings.DEBUG:
  urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)