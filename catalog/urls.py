from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    path('', views.CatalogView.as_view(), name='catalog'),
    path('product/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
]