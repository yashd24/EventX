from django.urls import path
from events.views import EventView, VenueView

urlpatterns = [
    # Unified event endpoints
    path('', EventView.as_view(), name='event-list'),
    path('<uuid:event_id>/', EventView.as_view(), name='event-detail'),
    path('venue/', VenueView.as_view(), name='venue-list'),
]
