"""Bills URL configuration."""

from django.urls import path
from . import views

urlpatterns = [
    path("categories", views.categories_view, name="categories"),
    path("home/picks", views.picks_view, name="picks"),
    path("bills", views.bills_list_view, name="bills-list"),
    path("bills/<str:bill_id>", views.bill_detail_view, name="bill-detail"),
    path("search", views.search_view, name="search"),
]
