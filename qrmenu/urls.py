"""
URL configuration for qrmenu project.
"""
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

urlpatterns = [
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('dashboard/', include('hotel.dashboard_urls')),
    path('api/', include('hotel.api_urls')),
    path('', include('hotel.urls')),
]

# Serve media files in both development and production
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
else:
    # Serve media files in production
    urlpatterns += [
        path(f'{settings.MEDIA_URL.strip("/")}/<path:path>', serve, {'document_root': settings.MEDIA_ROOT}),
    ]

