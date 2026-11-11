from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('cart/', views.CartView.as_view(), name='cart'),
    path('order/create/', views.OrderCreateView.as_view(), name='order_create'),
    path('orders/', views.OrderListView.as_view(), name='order_list'),
    path('order/<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('manager/orders/', views.ManagerOrderListView.as_view(), name='manager_order_list'),
    path('manager/order/<int:pk>/', views.ManagerOrderDetailView.as_view(), name='manager_order_detail'),
    path('manager/order-item/<int:pk>/delete/', views.OrderItemDeleteView.as_view(), name='order_item_delete'),
]