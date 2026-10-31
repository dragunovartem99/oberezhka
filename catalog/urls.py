from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("kukly/", views.catalog, name="catalog"),
    path("kukly/<slug:slug>/", views.doll, name="doll"),
    path("o-masterskoy/", views.about, name="about"),
    path("kak-zakazat/", views.ordering, name="ordering"),
]
