"""
Admin inventory management views
"""
from django.forms import model_to_dict
from django.utils import timezone
from django.db.models import Count
from EventX.helper import BaseAPIClass
from EventX.cache_utils import cache_api_response, invalidate_events_cache
from inventory.models import EventInventory, Seat, InventoryHold
from inventory.serializers import (
    EventInventoryStatusSerializer,
    SeatUpdateSerializer,
    SeatSerializer,
    InventoryHoldSerializer,
)
from events.models import Events
from accounts.models import User


class AdminInventoryManagementView(BaseAPIClass):
    """Unified admin view for managing event inventory"""

    @cache_api_response('admin_inventory_management', timeout=60)  # 1 minute cache
    def get(self, request, event_id):
        """
        Get inventory status for an event (admin only)
        """
        try:
            user = request.validated_user
            
            # Check if user is admin
            if user.user_type != User.USER_TYPE.ADMIN:
                self.message = "Admin access required"
                self.error_occurred(e=None, custom_code=6001)
                return self.get_response()
            
            # Get event
            try:
                event = Events.objects.get(events_id=event_id)
            except Events.DoesNotExist:
                self.message = "Event not found"
                self.error_occurred(e=None, custom_code=6002)
                return self.get_response()
            
            # Get inventory status
            inventories = EventInventory.objects.filter(event_id=event_id).select_related('ticket_type_id')
            inventory_serializer = EventInventoryStatusSerializer(inventories, many=True)
            
            # Get seat summary if reserved seating
            seat_summary = None
            if event.seat_mode == Events.SEAT_MODE.RESERVED_SEATING:
                seat_counts = Seat.objects.filter(event_id=event_id).values('status').annotate(
                    count=Count('seat_id')
                )
                seat_summary = {item['status']: item['count'] for item in seat_counts}
            
            self.data = {
                'event': {
                    'event_id': str(event.events_id),
                    'event_name': event.event_name,
                    'seat_mode': event.seat_mode,
                    'status': event.status
                },
                'inventories': inventory_serializer.data,
                'seat_summary': seat_summary,
                'total_holds': InventoryHold.objects.filter(
                    events_id=event_id,
                    status=InventoryHold.HOLD_STATUS.ACTIVE
                ).count()
            }
            self.message = "Inventory status retrieved successfully"
            
        except Exception as e:
            self.message = "Failed to retrieve inventory status"
            self.error_occurred(e, custom_code=6003)
        
        return self.get_response()


class AdminSeatManagementView(BaseAPIClass):
    """Admin view for managing seats"""

    def get(self, request, event_id):
        """
        Get all seats for an event
        """
        try:
            user = request.validated_user
            
            # Check if user is admin
            if user.user_type != User.USER_TYPE.ADMIN:
                self.message = "Admin access required"
                self.error_occurred(e=None, custom_code=6013)
                return self.get_response()
            
            # Get event
            try:
                event = Events.objects.get(events_id=event_id)
            except Events.DoesNotExist:
                self.message = "Event not found"
                self.error_occurred(e=None, custom_code=6014)
                return self.get_response()
            
            # Get seats
            seats = Seat.objects.filter(event_id=event_id).select_related('ticket_type_id')
            seat_serializer = SeatSerializer(seats, many=True)
            
            self.data = {
                'event': {
                    'event_id': str(event.events_id),
                    'event_name': event.event_name,
                    'seat_mode': event.seat_mode
                },
                'seats': seat_serializer.data,
                'total_seats': seats.count()
            }
            self.message = "Seats retrieved successfully"
            
        except Exception as e:
            self.message = "Failed to retrieve seats"
            self.error_occurred(e, custom_code=6015)
        
        return self.get_response()


class AdminSeatDetailView(BaseAPIClass):
    """Admin view for individual seat management"""

    def put(self, request, seat_id):
        """
        Update seat status or ticket type
        """
        try:
            user = request.validated_user
            
            # Check if user is admin
            if user.user_type != User.USER_TYPE.ADMIN:
                self.message = "Admin access required"
                self.error_occurred(e=None, custom_code=6020)
                return self.get_response()
            
            # Get seat
            try:
                seat = Seat.objects.get(seat_id=seat_id)
            except Seat.DoesNotExist:
                self.message = "Seat not found"
                self.error_occurred(e=None, custom_code=6021)
                return self.get_response()
            
            serializer = SeatUpdateSerializer(data=request.data)
            if serializer.is_valid():
                status = serializer.validated_data['status']
                ticket_type_id = serializer.validated_data.get('ticket_type_id')
                
                # Update seat
                seat.status = status
                if ticket_type_id is not None:
                    seat.ticket_type_id_id = ticket_type_id
                seat.save()
                
                # Invalidate cache
                invalidate_events_cache(event_id=seat.event_id.events_id)
                
                self.data = SeatSerializer(seat).data
                self.message = "Seat updated successfully"
                
            else:
                self.custom_code = 6022
                self._serializer_errors(serializer.errors)
                
        except Exception as e:
            self.message = "Failed to update seat"
            self.error_occurred(e, custom_code=6023)
        
        return self.get_response()


class AdminHoldManagementView(BaseAPIClass):
    """Admin view for managing inventory holds"""
    hold_serializer = InventoryHoldSerializer

    def get(self, request):
        """
        Get all active holds
        """
        try:
            user = request.validated_user
            
            # Check if user is admin
            if user.user_type != User.USER_TYPE.ADMIN:
                self.message = "Admin access required"
                self.error_occurred(e=None, custom_code=6028)
                return self.get_response()
            
            # Get query parameters
            event_id = request.GET.get('event_id')
            status = request.GET.get('status', 'active')
            
            # Build query
            holds_query = InventoryHold.objects.select_related(
                'user', 'events_id', 'ticket_type'
            ).prefetch_related('hold_seats__seat_id')
            
            if event_id:
                holds_query = holds_query.filter(events_id=event_id)
            
            if status == 'active':
                holds_query = holds_query.filter(status=InventoryHold.HOLD_STATUS.ACTIVE)
            elif status == 'expired':
                holds_query = holds_query.filter(
                    status=InventoryHold.HOLD_STATUS.ACTIVE,
                    expires_at__lt=timezone.now()
                )
            
            holds = model_to_dict(holds_query.order_by('-created_at'))
            
            self.data = {
                'holds': holds,
                'total_holds': holds.count(),
                'active_holds': holds.filter(status=InventoryHold.HOLD_STATUS.ACTIVE).count()
            }
            self.message = "Holds retrieved successfully"

        except Exception as e:
            self.message = "Failed to retrieve holds"
            self.error_occurred(e, custom_code=6029)
        
        return self.get_response()
