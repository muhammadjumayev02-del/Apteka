from catalog.admin import site
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path
from catalog.forms import UzbekAuthenticationForm

urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/", site.urls),
    path("kirish/", LoginView.as_view(authentication_form=UzbekAuthenticationForm), name="login"),
    path("chiqish/", LogoutView.as_view(), name="logout"),
    path("", include("catalog.urls")),
]
