"""
Serializers for inventory management
"""
from rest_framework import serializers
from inventory.models import EventInventory, Seat, InventoryHold
from events.models import Events, TicketType


class SeatUpdateSerializer(serializers.Serializer):
    """Serializer for updating seat status"""
    status = serializers.ChoiceField(
        choices=[(status.value, status.name) for status in Seat.SEAT_STATUS]
    )
    ticket_type_id = serializers.UUIDField(required=False, allow_null=True)
    
    def validate_ticket_type_id(self, value):
        if value:
            try:
                ticket_type = TicketType.objects.get(ticket_type_id=value)
                if not ticket_type.is_active:
                    raise serializers.ValidationError("Ticket type is not active")
            except TicketType.DoesNotExist:
                raise serializers.ValidationError("Ticket type not found")
        return value


class EventInventoryStatusSerializer(serializers.ModelSerializer):
    """Serializer for event inventory status"""
    ticket_type_name = serializers.CharField(source='ticket_type_id.ticket_type_name', read_only=True)
    ticket_type_price = serializers.IntegerField(source='ticket_type_id.price', read_only=True)
    available_qty = serializers.SerializerMethodField()
    
    class Meta:
        model = EventInventory
        fields = [
            'event_inventory_id', 'ticket_type_id', 'ticket_type_name', 
            'ticket_type_price', 'initial_qty', 'sold_qty', 'held_qty', 'available_qty'
        ]
    
    def get_available_qty(self, obj):
        return obj.initial_qty - obj.sold_qty - obj.held_qty


class SeatSerializer(serializers.ModelSerializer):
    """Serializer for seat data"""
    ticket_type_name = serializers.CharField(source='ticket_type_id.ticket_type_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Seat
        fields = [
            'seat_id', 'section', 'row_label', 'seat_number', 
            'ticket_type_id', 'ticket_type_name', 'status', 'status_display'
        ]


class InventoryHoldSerializer(serializers.ModelSerializer):
    """Serializer for inventory holds"""
    user_email = serializers.CharField(source='user.email', read_only=True)
    event_name = serializers.CharField(source='events_id.event_name', read_only=True)
    ticket_type_name = serializers.CharField(source='ticket_type.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    seats = SeatSerializer(source='hold_seats', many=True, read_only=True)
    time_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = InventoryHold
        fields = [
            'inventory_hold_id', 'user_email', 'event_name', 'ticket_type_name',
            'quantity', 'status', 'status_display', 'expires_at', 'time_remaining',
            'request_id', 'created_at', 'seats'
        ]
    
    def get_time_remaining(self, obj):
        from django.utils import timezone
        if obj.status == InventoryHold.HOLD_STATUS.ACTIVE:
            remaining = obj.expires_at - timezone.now()
            if remaining.total_seconds() > 0:
                return int(remaining.total_seconds())
        return 0

class EventAvailabilitySerializer(serializers.ModelSerializer):
    """Serializer for event availability information"""
    ticket_type_name = serializers.CharField(source='ticket_type_id.ticket_type_name', read_only=True)
    ticket_type_price = serializers.IntegerField(source='ticket_type_id.price', read_only=True)
    available_qty = serializers.SerializerMethodField()
    is_available = serializers.SerializerMethodField()
    
    class Meta:
        model = EventInventory
        fields = [
            'ticket_type_id', 'ticket_type_name', 'ticket_type_price',
            'initial_qty', 'sold_qty', 'held_qty', 'available_qty', 'is_available'
        ]
    
    def get_available_qty(self, obj):
        return obj.initial_qty - obj.sold_qty - obj.held_qty
    
    def get_is_available(self, obj):
        return self.get_available_qty(obj) > 0


class SeatAvailabilitySerializer(serializers.ModelSerializer):
    """Serializer for seat availability information"""
    ticket_type_name = serializers.CharField(source='ticket_type_id.ticket_type_name', read_only=True)
    ticket_type_price = serializers.IntegerField(source='ticket_type_id.price', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_available = serializers.SerializerMethodField()
    
    class Meta:
        model = Seat
        fields = [
            'seat_id', 'section', 'row_label', 'seat_number',
            'ticket_type_id', 'ticket_type_name', 'ticket_type_price',
            'status', 'status_display', 'is_available'
        ]
    
    def get_is_available(self, obj):
        return obj.status == Seat.SEAT_STATUS.AVAILABLE


class HoldCreateSerializer(serializers.Serializer):
    """Serializer for creating inventory holds"""
    event_id = serializers.UUIDField()
    ticket_type_id = serializers.UUIDField(required=False, allow_null=True)
    quantity = serializers.IntegerField(min_value=1, max_value=10)
    seat_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True
    )
    
    def validate_event_id(self, value):
        try:
            event = Events.objects.get(events_id=value)
            if event.status != Events.EVENT_STATUS.PUBLISHED:
                raise serializers.ValidationError("Event is not available for booking")
            return value
        except Events.DoesNotExist:
            raise serializers.ValidationError("Event not found")
    
    def validate_ticket_type_id(self, value):
        if value:
            try:
                ticket_type = TicketType.objects.get(ticket_type_id=value)
                if not ticket_type.is_active:
                    raise serializers.ValidationError("Ticket type is not active")
            except TicketType.DoesNotExist:
                raise serializers.ValidationError("Ticket type not found")
        return value
    
    def validate(self, data):
        event_id = data['event_id']
        ticket_type_id = data.get('ticket_type_id')
        quantity = data['quantity']
        seat_ids = data.get('seat_ids', [])
        
        # Get event
        event = Events.objects.get(events_id=event_id)
        
        if event.seat_mode == Events.SEAT_MODE.GENERAL_ADMISSION:
            # General admission - check inventory
            if not ticket_type_id:
                raise serializers.ValidationError("Ticket type is required for general admission events")
            
            try:
                inventory = EventInventory.objects.get(
                    event_id=event_id,
                    ticket_type_id=ticket_type_id
                )
                available_qty = inventory.initial_qty - inventory.sold_qty - inventory.held_qty
                if available_qty < quantity:
                    raise serializers.ValidationError(
                        f"Only {available_qty} tickets available, requested {quantity}"
                    )
            except EventInventory.DoesNotExist:
                raise serializers.ValidationError("No inventory available for this ticket type")
        
        elif event.seat_mode == Events.SEAT_MODE.RESERVED_SEATING:
            # Reserved seating - check seats
            if not seat_ids:
                raise serializers.ValidationError("Seat selection is required for reserved seating events")
            
            if len(seat_ids) != quantity:
                raise serializers.ValidationError("Number of seats must match quantity")
            
            # Check if seats are available
            available_seats = Seat.objects.filter(
                event_id=event_id,
                seat_id__in=seat_ids,
                status=Seat.SEAT_STATUS.AVAILABLE
            )
            
            if available_seats.count() != len(seat_ids):
                raise serializers.ValidationError("Some selected seats are not available")
            
            # Check if all seats have same ticket type (if specified)
            if ticket_type_id:
                seats_with_different_type = available_seats.exclude(ticket_type_id=ticket_type_id)
                if seats_with_different_type.exists():
                    raise serializers.ValidationError("All selected seats must be of the same ticket type")
        
        return data


