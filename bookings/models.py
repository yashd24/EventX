import enum
from uuid import uuid4
from django.db import models
from django_enumfield import enum
from accounts.models import User
from events.models import Events, TicketType
from inventory.models import Seat, InventoryHold


class Booking(models.Model):

    class BOOKING_STATUS(enum.Enum):
        PENDING = 1
        CONFIRMED = 2
        CANCELLED = 3
        EXPIRED = 4
        FAILED = 5
    
    booking_id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookings")
    events_id = models.ForeignKey(Events, on_delete=models.CASCADE, related_name="bookings")
    status = enum.EnumField(BOOKING_STATUS, default=BOOKING_STATUS.PENDING)
    total_price_cents = models.PositiveIntegerField(default=0)
    currency = models.CharField(max_length=3, default="USD")
    hold_id = models.OneToOneField(InventoryHold, on_delete=models.SET_NULL, null=True, blank=True, related_name="booking")
    request_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "booking"


class BookingItem(models.Model):
    booking_item_id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    booking_id = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="items")
    ticket_type_id = models.ForeignKey(TicketType, on_delete=models.SET_NULL, null=True, blank=True)
    seat_id = models.ForeignKey(Seat, on_delete=models.SET_NULL, null=True, blank=True)
    price_cents = models.PositiveIntegerField()
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "booking_item"


class Cancellation(models.Model):
    cancellation_id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    booking_id = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="cancellations")
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cancellation"


class EventWaitlist(models.Model):

    class WAITLIST_STATUS(enum.Enum):
        ACTIVE = 1
        NOTIFIED = 2
        CONSUMED = 3
        EXPIRED = 4

    event_waitlist_id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    events_id = models.ForeignKey(Events, on_delete=models.CASCADE, related_name="waitlist")
    ticket_type_id = models.ForeignKey(TicketType, on_delete=models.SET_NULL, null=True, blank=True)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, related_name="waitlist_entries")
    position = models.PositiveIntegerField()
    status = enum.EnumField(WAITLIST_STATUS, default=WAITLIST_STATUS.ACTIVE)
    notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "event_waitlist"
        unique_together = ("events_id", "ticket_type_id", "user_id")
