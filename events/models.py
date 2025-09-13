from uuid import uuid4
from django.db import models
from django_enumfield import enum

class Venue(models.Model):
    venue_id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    capacity_hint = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "venue"
   
    def __str__(self):
        return self.name


class Events(models.Model):

    class SEAT_MODE(enum.Enum):
        GENERAL_ADMISSION = 1
        RESERVED_SEATING = 2

    class EVENT_STATUS(enum.Enum):
        DRAFT = 1
        PUBLISHED = 2
        CANCELLED = 3
        ENDED = 4

    events_id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    venue_id = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="events")
    event_name = models.CharField(max_length=255)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    seat_mode = enum.EnumField(SEAT_MODE, default=SEAT_MODE.GENERAL_ADMISSION)
    status = enum.EnumField(EVENT_STATUS, default=EVENT_STATUS.PUBLISHED)
    sales_starts_at = models.DateTimeField(null=True, blank=True)
    sales_ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "events"

    def __str__(self):
        return f"{self.event_name} @ {self.venue_id.name}"


class TicketType(models.Model):
    ticket_type_id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    events_id = models.ForeignKey(Events, on_delete=models.CASCADE, related_name="ticket_types")
    ticket_type_name = models.CharField(max_length=100)
    price = models.PositiveIntegerField()
    currency = models.CharField(max_length=5, default="INR")
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "ticket_type"

    def __str__(self):
        return f"{self.ticket_type_name} - {self.events_id.event_name}"
