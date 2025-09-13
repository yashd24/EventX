from rest_framework import serializers
from bookings.models import Booking, BookingItem
from events.models import Events, TicketType
from inventory.models import Seat


class CreateBookingSerializer(serializers.Serializer):
    event_id = serializers.UUIDField()
    ticket_type_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=10)
    seat_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True
    )

    def validate(self, data):
        event_id = data.get('event_id')
        ticket_type_id = data.get('ticket_type_id')
        quantity = data.get('quantity')
        seat_ids = data.get('seat_ids', [])

        # Validate event exists and is active
        try:
            event = Events.objects.get(events_id=event_id)
            if event.status != Events.EVENT_STATUS.PUBLISHED:
                raise serializers.ValidationError("Event is not available for booking")
        except Events.DoesNotExist:
            raise serializers.ValidationError("Event not found")

        # Validate ticket type exists and belongs to event
        try:
            ticket_type = TicketType.objects.get(
                ticket_type_id=ticket_type_id,
                events_id=event_id,
                is_active=True
            )
        except TicketType.DoesNotExist:
            raise serializers.ValidationError("Invalid ticket type for this event")

        # Validate seat allocation based on seat mode
        if event.seat_mode == Events.SEAT_MODE.RESERVED_SEATING:
            if not seat_ids:
                raise serializers.ValidationError("Seat selection required for reserved seating")
            if len(seat_ids) != quantity:
                raise serializers.ValidationError("Number of seats must match quantity")
            
            # Validate seats exist and belong to event
            seats = Seat.objects.filter(
                seat_id__in=seat_ids,
                events_id=event_id,
                ticket_type_id=ticket_type_id
            )
            if seats.count() != len(seat_ids):
                raise serializers.ValidationError("Invalid seat selection")
        else:  # General Admission
            if seat_ids:
                raise serializers.ValidationError("Seat selection not allowed for general admission")

        return data


class BookingItemSerializer(serializers.ModelSerializer):
    ticket_type_name = serializers.CharField(source='ticket_type_id.ticket_type_name', read_only=True)
    seat_info = serializers.SerializerMethodField()

    class Meta:
        model = BookingItem
        fields = ['booking_item_id', 'ticket_type_id', 'seat_id', 'price_cents', 'quantity', 'ticket_type_name', 'seat_info']

    def get_seat_info(self, obj):
        if obj.seat_id:
            return {
                'section': obj.seat_id.section,
                'row': obj.seat_id.row_label,
                'seat_number': obj.seat_id.seat_number
            }
        return None


class BookingSerializer(serializers.ModelSerializer):
    items = BookingItemSerializer(many=True, read_only=True)
    event_name = serializers.CharField(source='events_id.event_name', read_only=True)
    venue_name = serializers.CharField(source='events_id.venue_id.name', read_only=True)
    event_date = serializers.DateTimeField(source='events_id.starts_at', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'booking_id', 'events_id', 'status', 'total_price_cents', 'currency',
            'request_id', 'created_at', 'confirmed_at', 'cancelled_at',
            'items', 'event_name', 'venue_name', 'event_date'
        ]


class BookingHistorySerializer(serializers.Serializer):
    page = serializers.IntegerField(min_value=1, default=1)
    rows_per_page = serializers.IntegerField(default=10, min_value=1, max_value=100)
    status = serializers.ChoiceField(
        choices=Booking.BOOKING_STATUS.values,
        required=False
    )
