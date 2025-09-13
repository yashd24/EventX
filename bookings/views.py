import uuid
from django.db import transaction
from django.utils import timezone
from django.db.models import F, Q
from EventX.helper import BaseAPIClass
from EventX.utils import paginate_queryset
from bookings.models import Booking, BookingItem, Cancellation
from bookings.serializers import (
    CreateBookingSerializer, 
    BookingSerializer, 
    BookingHistorySerializer
)
from events.models import Events, TicketType
from inventory.models import Seat, InventoryHold, EventInventory
from accounts.models import User


class BookingView(BaseAPIClass):
    model_class = Booking
    create_serializer = CreateBookingSerializer
    fetch_serializer = BookingHistorySerializer

    def post(self, request):
        """
        Create a new booking with seat allocation
        """
        try:
            user = request.validated_user
            serializer = self.create_serializer(data=request.data)
            
            if serializer.is_valid():
                validated_data = serializer.validated_data
                event_id = validated_data['event_id']
                ticket_type_id = validated_data['ticket_type_id']
                quantity = validated_data['quantity']
                seat_ids = validated_data.get('seat_ids', [])
                
                # Generate unique request ID for this booking attempt
                request_id = str(uuid.uuid4())
                
                # Use database transaction with locking to prevent race conditions
                with transaction.atomic():
                    # Lock the event and ticket type for updates
                    event = Events.objects.select_for_update().get(events_id=event_id)
                    ticket_type = TicketType.objects.select_for_update().get(
                        ticket_type_id=ticket_type_id
                    )
                    
                    # Check if event is still available for booking
                    if event.status != Events.EVENT_STATUS.PUBLISHED:
                        self.error_occurred(
                            e=None, 
                            message="Event is no longer available for booking", 
                            custom_code=4101
                        )
                        return self.get_response()
                    
                    # Check sales window
                    now = timezone.now()
                    if event.sales_starts_at and now < event.sales_starts_at:
                        self.error_occurred(
                            e=None, 
                            message="Booking not yet open", 
                            custom_code=4102
                        )
                        return self.get_response()
                    
                    if event.sales_ends_at and now > event.sales_ends_at:
                        self.error_occurred(
                            e=None, 
                            message="Booking window has closed", 
                            custom_code=4103
                        )
                        return self.get_response()
                    
                    # Handle seat allocation based on seat mode
                    if event.seat_mode == Events.SEAT_MODE.RESERVED_SEATING:
                        # Lock and allocate specific seats
                        seats = Seat.objects.select_for_update().filter(
                            seat_id__in=seat_ids,
                            event_id=event_id,
                            ticket_type_id=ticket_type_id,
                            status=Seat.SEAT_STATUS.AVAILABLE
                        )
                        
                        if seats.count() != len(seat_ids):
                            self.error_occurred(
                                e=None, 
                                message="Some seats are no longer available", 
                                custom_code=4104
                            )
                            return self.get_response()
                        
                        # Create inventory hold for seats
                        hold = InventoryHold.objects.create(
                            events_id=event,
                            user=user,
                            ticket_type=ticket_type,
                            quantity=0,  # Reserved seating uses individual seats
                            status=InventoryHold.HOLD_STATUS.ACTIVE,
                            expires_at=now + timezone.timedelta(minutes=15),  # 15 min hold
                            request_id=request_id
                        )
                        
                        # Create hold-seat relationships
                        for seat in seats:
                            hold.seats.create(seat_id=seat)
                            seat.status = Seat.SEAT_STATUS.HELD
                            seat.save()
                    
                    else:  # General Admission
                        # Check and allocate from inventory
                        inventory = EventInventory.objects.select_for_update().get(
                            event_id=event_id,
                            ticket_type_id=ticket_type_id
                        )
                        
                        available_qty = inventory.initial_qty - inventory.sold_qty - inventory.held_qty
                        if available_qty < quantity:
                            self.error_occurred(
                                e=None, 
                                message=f"Only {available_qty} tickets available", 
                                custom_code=4105
                            )
                            return self.get_response()
                        
                        # Create inventory hold
                        hold = InventoryHold.objects.create(
                            events_id=event,
                            user=user,
                            ticket_type=ticket_type,
                            quantity=quantity,
                            status=InventoryHold.HOLD_STATUS.ACTIVE,
                            expires_at=now + timezone.timedelta(minutes=15),  # 15 min hold
                            request_id=request_id
                        )
                        
                        # Update held quantity
                        inventory.held_qty = F('held_qty') + quantity
                        inventory.save()
                    
                    # Create booking
                    total_price = ticket_type.price * quantity
                    booking = Booking.objects.create(
                        user_id=user,
                        events_id=event,
                        status=Booking.BOOKING_STATUS.PENDING,
                        total_price_cents=total_price,
                        currency=ticket_type.currency,
                        hold_id=hold,
                        request_id=request_id
                    )
                    
                    # Create booking items
                    if event.seat_mode == Events.SEAT_MODE.RESERVED_SEATING:
                        # One item per seat
                        for seat in seats:
                            BookingItem.objects.create(
                                booking_id=booking,
                                ticket_type_id=ticket_type,
                                seat_id=seat,
                                price_cents=ticket_type.price,
                                quantity=1
                            )
                    else:
                        # Single item with quantity
                        BookingItem.objects.create(
                            booking_id=booking,
                            ticket_type_id=ticket_type,
                            price_cents=ticket_type.price,
                            quantity=quantity
                        )
                    
                    # Serialize and return booking data
                    booking_serializer = BookingSerializer(booking)
                    self.data = booking_serializer.data
                    self.message = "Booking created successfully. Please complete payment within 15 minutes."
                    
            else:
                self.custom_code = 4106
                self._serializer_errors(serializer.errors)
                
        except Events.DoesNotExist:
            self.error_occurred(e=None, message="Event not found", custom_code=4107)
        except TicketType.DoesNotExist:
            self.error_occurred(e=None, message="Ticket type not found", custom_code=4108)
        except EventInventory.DoesNotExist:
            self.error_occurred(e=None, message="Event inventory not found", custom_code=4109)
        except Exception as e:
            self.error_occurred(e, message="Booking creation failed", custom_code=4110)
        
        return self.get_response()

    def get(self, request):
        """
        Get user's booking history
        """
        try:
            user = request.validated_user
            serializer = self.fetch_serializer(data=request.GET)
            
            if serializer.is_valid():
                validated_data = serializer.validated_data
                page = validated_data.get('page', 1)
                rows_per_page = validated_data.get('rows_per_page', 10)
                status_filter = validated_data.get('status')
                
                # Build query
                queryset = self.model_class.objects.filter(user_id=user).order_by('-created_at')
                
                if status_filter:
                    queryset = queryset.filter(status=status_filter)
                
                # Paginate results
                paginated_data = paginate_queryset(queryset, page, rows_per_page)
                
                # Serialize bookings
                bookings_serializer = BookingSerializer(paginated_data['results'], many=True)
                
                self.data = {
                    'bookings': bookings_serializer.data,
                    'pagination': {
                        'current_page': page,
                        'total_pages': paginated_data['total_pages'],
                        'total_count': paginated_data['total_count'],
                        'has_next': paginated_data['has_next'],
                        'has_previous': paginated_data['has_previous']
                    }
                }
                self.message = "Booking history retrieved successfully"
                
            else:
                self.custom_code = 4111
                self._serializer_errors(serializer.errors)
                
        except Exception as e:
            self.error_occurred(e, message="Failed to retrieve booking history", custom_code=4112)
        
        return self.get_response()


class BookingDetailView(BaseAPIClass):
    model_class = Booking

    def delete(self, request, booking_id):
        """
        Cancel a booking
        """
        try:
            user = request.validated_user
            
            with transaction.atomic():
                # Get booking with lock
                booking = self.model_class.objects.select_for_update().get(
                    booking_id=booking_id,
                    user_id=user
                )
                
                # Check if booking can be cancelled
                if booking.status == Booking.BOOKING_STATUS.CANCELLED:
                    self.error_occurred(
                        e=None, 
                        message="Booking is already cancelled", 
                        custom_code=4121
                    )
                    return self.get_response()
                
                if booking.status == Booking.BOOKING_STATUS.EXPIRED:
                    self.error_occurred(
                        e=None, 
                        message="Booking has expired", 
                        custom_code=4122
                    )
                    return self.get_response()
                
                # Update booking status
                booking.status = Booking.BOOKING_STATUS.CANCELLED
                booking.cancelled_at = timezone.now()
                booking.save()
                
                # Release inventory hold
                if booking.hold_id:
                    hold = booking.hold_id
                    hold.status = InventoryHold.HOLD_STATUS.CANCELLED
                    hold.save()
                    
                    # Release seats or inventory
                    if hold.seats.exists():
                        # Release reserved seats
                        for hold_seat in hold.seats.all():
                            seat = hold_seat.seat_id
                            seat.status = Seat.SEAT_STATUS.AVAILABLE
                            seat.save()
                    else:
                        # Release general admission inventory
                        inventory = EventInventory.objects.get(
                            event_id=hold.events_id,
                            ticket_type_id=hold.ticket_type
                        )
                        inventory.held_qty = F('held_qty') - hold.quantity
                        inventory.save()
                
                # Create cancellation record
                Cancellation.objects.create(
                    booking_id=booking,
                    reason="User requested cancellation"
                )
                
                self.message = "Booking cancelled successfully"
                
        except self.model_class.DoesNotExist:
            self.error_occurred(e=None, message="Booking not found", custom_code=4123)
        except Exception as e:
            self.error_occurred(e, message="Booking cancellation failed", custom_code=4124)
        
        return self.get_response()
