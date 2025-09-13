from django.urls import path
from bookings.views import BookingView, BookingDetailView

urlpatterns = [
    path('', BookingView.as_view(), name='booking-list'),
    path('<uuid:booking_id>/', BookingDetailView.as_view(), name='booking-detail'),
]
