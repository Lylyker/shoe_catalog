from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.DashboardHome.as_view(), name='home'),
    path('e/<slug:slug>/', views.EntityList.as_view(), name='list'),
    path('e/<slug:slug>/add/', views.EntityCreate.as_view(), name='create'),
    path('e/<slug:slug>/bulk-delete/', views.BulkDelete.as_view(), name='bulk-delete'),
    path('e/<slug:slug>/<int:pk>/', views.EntityDetail.as_view(), name='detail'),
    path('e/<slug:slug>/<int:pk>/edit/', views.EntityUpdate.as_view(), name='update'),
    path('e/<slug:slug>/<int:pk>/delete/', views.EntityDelete.as_view(), name='delete'),
    path('supply/<int:pk>/<slug:action>/', views.SupplyAction.as_view(), name='supply-action'),
    path('order/<int:pk>/item/add/', views.OrderItemAdd.as_view(), name='order-item-add'),
    path('order/item/<int:pk>/remove/', views.OrderItemRemove.as_view(), name='order-item-remove'),
    path('stock/<int:pk>/adjust/', views.StockAdjust.as_view(), name='stock-adjust'),
]