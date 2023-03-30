from django.conf import settings
from django.urls import path, include
from django.conf.urls.static import static
from django.contrib import admin

from rest_framework import permissions

from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from drf_spectacular.views import (
   SpectacularAPIView,
   SpectacularSwaggerView,
)

# Swagger
schema_view = get_schema_view(
   openapi.Info(
      title="Validation Server API",
      default_version='v1',
      description="API for Validation Server",
      terms_of_service="https://www.urban.org/terms-service",
      contact=openapi.Contact(email="validation-server@urban.org"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.IsAuthenticated,),
)

#router = DefaultRouter()

urlpatterns = [
   path('api/admin/', admin.site.urls),
   path('api/schema/', SpectacularAPIView.as_view(), name='api-schema'),
   path(
      'api/docs/',
      SpectacularSwaggerView.as_view(url_name='api-schema'),
      name='api-docs'
   ),
   path('api/users/', include('users.urls')),
   path('api/job/', include('job.urls')),
   path('api/budget/', include('budget.urls'))
]

if settings.DEBUG:
   urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
   urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
   
