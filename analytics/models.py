from uuid import uuid4
from django.db import models
from django_enumfield import enum
from events.models import Events

class BookingFact(models.Model):
    
    class ACTION(enum.Enum):
        BOOKING_CONFIRMED = 1
        BOOKING_CANCELLED = 2

    booking_fact_id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    event_id = models.ForeignKey(Events, on_delete=models.CASCADE, related_name="booking_facts")
    booking_id = models.BigIntegerField()
    occurred_at = models.DateTimeField()
    action = enum.EnumField(ACTION, default=ACTION.BOOKING_CANCELLED)  # BOOKING_CONFIRMED | BOOKING_CANCELLED
    tickets = models.PositiveIntegerField()
    amount_cents = models.PositiveIntegerField()

    class Meta:
        db_table = "booking_fact"


class EventDailyRollup(models.Model):

    event_daily_rollup_id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    event_id = models.ForeignKey(Events, on_delete=models.CASCADE, related_name="event_daily_rollups")
    day = models.DateField()
    bookings = models.PositiveIntegerField()
    cancellations = models.PositiveIntegerField()
    tickets_sold = models.PositiveIntegerField()
    revenue = models.PositiveIntegerField()

    class Meta:
        db_table = "event_daily_rollup"
        unique_together = ("event_id", "day")
