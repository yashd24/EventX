"""
URL patterns for inventory management
"""
from django.urls import path
from inventory.views import (
    AdminInventoryManagementView,
    AdminSeatManagementView,
    AdminSeatDetailView,
    AdminHoldManagementView
)
from inventory.user_views import (
    EventAvailabilityView,
    UserHoldCreateView,
    UserHoldListView
)

urlpatterns = [
    # Unified inventory management (admin + user)
    path('events/<uuid:event_id>/availability/', EventAvailabilityView.as_view(), name='event-availability'),
    path('admin/events/<uuid:event_id>/inventory/', AdminInventoryManagementView.as_view(), name='admin-inventory-management'),
    
    # Seat management
    path('admin/events/<uuid:event_id>/seats/', AdminSeatManagementView.as_view(), name='admin-seat-management'),
    path('admin/seats/<uuid:seat_id>/', AdminSeatDetailView.as_view(), name='admin-seat-detail'),
    
    # Hold management
    path('admin/holds/', AdminHoldManagementView.as_view(), name='admin-hold-management'),
    path('admin/holds/<uuid:hold_id>/expire/', AdminHoldManagementView.as_view(), name='admin-hold-expire'),
    
    # User hold management
    path('holds/create/', UserHoldCreateView.as_view(), name='user-hold-create'),
    path('holds/', UserHoldListView.as_view(), name='user-hold-list'),
]
