from django.urls import path
from . import views

app_name = "catalog"
urlpatterns = [
    path("savat/", views.cart, name="cart"),
    path("hisobotlar/", views.reports, name="reports"),
    path("smenalar/jadval/yangi/", views.schedule_create, name="schedule_create"),
    path("smenalar/", views.shifts, name="shifts"),
    path("smenalar/<int:pk>/", views.shift_detail, name="shift_detail"),
    path("sotuv/tasdiqlash/", views.sale_confirm, name="sale_confirm"),
    path("sotuv/<int:pk>/bekor/", views.sale_cancel, name="sale_cancel"),
    path("dorilar/<int:pk>/joylar/", views.locations, name="locations"),
    path("dorilar/<int:pk>/sotish/", views.sell, name="sell"),
    path("dorilar/<int:pk>/kochirish/", views.transfer, name="transfer"),
    path("", views.home, name="home"),
    path("dorilar/yangi/", views.edit, name="create"),
    path("dorilar/<int:pk>/", views.detail, name="detail"),
    path("dorilar/<int:pk>/tahrirlash/", views.edit, name="edit"),
]
