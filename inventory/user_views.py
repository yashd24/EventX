"""
User-facing inventory management views
"""
from django.db import transaction
from django.utils import timezone
from EventX.helper import BaseAPIClass
from EventX.cache_utils import cache_api_response, invalidate_events_cache, invalidate_bookings_cache
from inventory.models import EventInventory, Seat, InventoryHold, InventoryHoldSeat
from inventory.serializers import (
    EventAvailabilitySerializer,
    SeatAvailabilitySerializer,
    HoldCreateSerializer,
    UserHoldSerializer,
)
from events.models import Events
from accounts.models import User
import uuid


class EventAvailabilityView(BaseAPIClass):
    """Unified view for checking event availability (admin + user)"""

    @cache_api_response('event_availability', timeout=30)  # 30 seconds cache
    def get(self, request, event_id):
        """
        Get availability information for an event
        """
        try:
            user = request.validated_user
            is_admin = user and user.user_type == User.USER_TYPE.ADMIN
            
            # Get event
            try:
                event = Events.objects.get(events_id=event_id)
            except Events.DoesNotExist:
                self.message = "Event not found"
                self.error_occurred(e=None, custom_code=7001)
                return self.get_response()
            
            # Check if event is published (only for non-admin users)
            if not is_admin and event.status != Events.EVENT_STATUS.PUBLISHED:
                self.message = "Event is not available for booking"
                self.error_occurred(e=None, custom_code=7002)
                return self.get_response()
            
            # Get availability data
            if event.seat_mode == Events.SEAT_MODE.GENERAL_ADMISSION:
                # General admission - get inventory
                inventories = EventInventory.objects.filter(
                    event_id=event_id
                ).select_related('ticket_type_id')
                
                ticket_types = EventAvailabilitySerializer(inventories, many=True).data
                total_available = sum(item['available_qty'] for item in ticket_types)
                
                response_data = {
                    'event': {
                        'event_id': str(event.events_id),
                        'event_name': event.event_name,
                        'event_date': event.event_date,
                        'venue_name': event.venue_id.name,
                        'seat_mode': event.seat_mode
                    },
                    'availability': {
                        'total_available': total_available,
                        'ticket_types': ticket_types
                    }
                }
                
                # Add admin-specific data if user is admin
                if is_admin:
                    response_data['admin_data'] = {
                        'status': event.status,
                        'total_holds': InventoryHold.objects.filter(
                            events_id=event_id,
                            status=InventoryHold.HOLD_STATUS.ACTIVE
                        ).count()
                    }
                
                self.data = response_data
                
            elif event.seat_mode == Events.SEAT_MODE.RESERVED_SEATING:
                # Reserved seating - get seats
                seats = Seat.objects.filter(
                    event_id=event_id,
                    status=Seat.SEAT_STATUS.AVAILABLE
                ).select_related('ticket_type_id')
                
                seats_data = SeatAvailabilitySerializer(seats, many=True).data
                total_available = len(seats_data)
                
                # Group by ticket type
                ticket_types = {}
                for seat in seats_data:
                    ticket_type_id = seat['ticket_type_id']
                    if ticket_type_id not in ticket_types:
                        ticket_types[ticket_type_id] = {
                            'ticket_type_id': ticket_type_id,
                            'ticket_type_name': seat['ticket_type_name'],
                            'ticket_type_price': seat['ticket_type_price'],
                            'available_seats': 0,
                            'seats': []
                        }
                    ticket_types[ticket_type_id]['available_seats'] += 1
                    ticket_types[ticket_type_id]['seats'].append(seat)
                
                response_data = {
                    'event': {
                        'event_id': str(event.events_id),
                        'event_name': event.event_name,
                        'event_date': event.event_date,
                        'venue_name': event.venue_id.name,
                        'seat_mode': event.seat_mode
                    },
                    'availability': {
                        'total_available': total_available,
                        'ticket_types': list(ticket_types.values())
                    }
                }
                
                # Add admin-specific data if user is admin
                if is_admin:
                    response_data['admin_data'] = {
                        'status': event.status,
                        'total_holds': InventoryHold.objects.filter(
                            events_id=event_id,
                            status=InventoryHold.HOLD_STATUS.ACTIVE
                        ).count()
                    }
                
                self.data = response_data
            
            self.message = "Event availability retrieved successfully"
            
        except Exception as e:
            self.message = "Failed to retrieve event availability"
            self.error_occurred(e, custom_code=7003)
        
        return self.get_response()


class UserHoldCreateView(BaseAPIClass):
    """User view for creating inventory holds"""

    def post(self, request):
        """
        Create a new inventory hold
        """
        try:
            user = request.validated_user
            
            # Check if user is authenticated
            if not user:
                self.message = "Authentication required"
                self.error_occurred(e=None, custom_code=7008)
                return self.get_response()
            
            serializer = HoldCreateSerializer(data=request.data)
            if serializer.is_valid():
                event_id = serializer.validated_data['event_id']
                ticket_type_id = serializer.validated_data.get('ticket_type_id')
                quantity = serializer.validated_data['quantity']
                seat_ids = serializer.validated_data.get('seat_ids', [])
                
                # Get event
                event = Events.objects.get(events_id=event_id)
                
                # Generate unique request ID
                request_id = uuid.uuid4()
                
                with transaction.atomic():
                    # Create hold
                    hold = InventoryHold.objects.create(
                        events_id=event,
                        user=user,
                        ticket_type_id=ticket_type_id,
                        quantity=quantity,
                        expires_at=timezone.now() + timezone.timedelta(minutes=10),
                        request_id=request_id
                    )
                    
                    if event.seat_mode == Events.SEAT_MODE.RESERVED_SEATING and seat_ids:
                        # Reserve specific seats
                        seats = Seat.objects.filter(
                            seat_id__in=seat_ids,
                            status=Seat.SEAT_STATUS.AVAILABLE
                        ).select_for_update()
                        
                        for seat in seats:
                            seat.status = Seat.SEAT_STATUS.HELD
                            seat.save()
                            
                            # Create hold-seat relationship
                            InventoryHoldSeat.objects.create(
                                hold_id=hold,
                                seat_id=seat
                            )
                    
                    elif event.seat_mode == Events.SEAT_MODE.GENERAL_ADMISSION:
                        # Update inventory hold quantity
                        inventory = EventInventory.objects.get(
                            event_id=event_id,
                            ticket_type_id=ticket_type_id
                        )
                        inventory.held_qty += quantity
                        inventory.save()
                
                # Invalidate cache
                invalidate_events_cache(event_id=event_id)
                invalidate_bookings_cache(user_id=user.user_id, event_id=event_id)
                
                self.data = {
                    'hold_id': str(hold.inventory_hold_id),
                    'request_id': str(request_id),
                    'expires_at': hold.expires_at,
                    'time_remaining': 600,  # 10 minutes in seconds
                    'quantity': quantity,
                    'seat_ids': seat_ids
                }
                self.message = "Hold created successfully"
                
            else:
                self.custom_code = 7009
                self._serializer_errors(serializer.errors)
                
        except Exception as e:
            self.message = "Failed to create hold"
            self.error_occurred(e, custom_code=7010)
        
        return self.get_response()


class UserHoldListView(BaseAPIClass):
    """User view for listing their holds"""

    @cache_api_response('user_holds', timeout=30, vary_on_user=True)
    def get(self, request):
        """
        Get user's active holds
        """
        try:
            user = request.validated_user
            
            # Check if user is authenticated
            if not user:
                self.message = "Authentication required"
                self.error_occurred(e=None, custom_code=7015)
                return self.get_response()
            
            # Get query parameters
            status = request.GET.get('status', 'active')
            
            # Build query
            holds_query = InventoryHold.objects.filter(user=user).select_related(
                'events_id', 'events_id__venue_id', 'ticket_type'
            ).prefetch_related('hold_seats__seat_id')
            
            if status == 'active':
                holds_query = holds_query.filter(status=InventoryHold.HOLD_STATUS.ACTIVE)
            elif status == 'all':
                pass  # Get all holds
            
            holds = holds_query.order_by('-created_at')
            holds_data = UserHoldSerializer(holds, many=True).data
            
            self.data = {
                'holds': holds_data,
                'total_holds': holds.count(),
                'active_holds': holds.filter(status=InventoryHold.HOLD_STATUS.ACTIVE).count()
            }
            self.message = "Holds retrieved successfully"
            
        except Exception as e:
            self.message = "Failed to retrieve holds"
            self.error_occurred(e, custom_code=7016)
        
        return self.get_response()
