from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from crm.telegram_webhook import telegram_webhook

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('crm.urls')),
    path('telegram/webhook/', telegram_webhook, name='telegram_webhook'),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)