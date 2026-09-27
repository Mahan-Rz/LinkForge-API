from django.contrib import admin
from django.urls import include, path

from core.views import redirect_shortened_url

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
    path('<str:shortened_code>/', redirect_shortened_url, name='url-redirect'),
]