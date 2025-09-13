from uuid import uuid4
from django.db import models
from events.models import Events, TicketType
from accounts.models import User
from django_enumfield import enum


class EventInventory(models.Model):
    event_inventory_id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    event_id = models.ForeignKey(Events, on_delete=models.CASCADE, related_name="inventories")
    ticket_type_id = models.ForeignKey(TicketType, on_delete=models.CASCADE, related_name="inventories")
    initial_qty = models.PositiveIntegerField()
    sold_qty = models.PositiveIntegerField(default=0)
    held_qty = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "event_inventory"
        unique_together = ("event_id", "ticket_type_id")



class Seat(models.Model):

    class SEAT_STATUS(enum.Enum):
        AVAILABLE = 1
        HELD = 2
        SOLD = 3
        BLOCKED = 4
    
    seat_id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    event_id = models.ForeignKey(Events, on_delete=models.CASCADE, related_name="seats")
    section = models.CharField(max_length=50, blank=True)
    row_label = models.CharField(max_length=20, blank=True)
    seat_number = models.CharField(max_length=20, blank=True)
    ticket_type_id = models.ForeignKey(TicketType, on_delete=models.SET_NULL, null=True, blank=True)
    status = enum.EnumField(SEAT_STATUS, default=SEAT_STATUS.AVAILABLE)

    class Meta:
        db_table = "seat"
        unique_together = ("event_id", "section", "row_label", "seat_number")


class InventoryHold(models.Model):

    class HOLD_STATUS(enum.Enum):
        ACTIVE = 1
        CONSUMED = 2
        EXPIRED = 3
        CANCELLED = 4

    inventory_hold_id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    events_id = models.ForeignKey(Events, on_delete=models.CASCADE, related_name="holds")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="holds")
    ticket_type = models.ForeignKey(TicketType, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=0)  # GA only
    status = enum.EnumField(HOLD_STATUS, default=HOLD_STATUS.ACTIVE)
    expires_at = models.DateTimeField()
    request_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "inventory_hold"


class InventoryHoldSeat(models.Model):
    inventory_hold_seat_id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    hold_id = models.ForeignKey(InventoryHold, on_delete=models.CASCADE, related_name="seats")
    seat_id = models.ForeignKey(Seat, on_delete=models.RESTRICT, related_name="hold_seats")

    class Meta:
        db_table = "inventory_hold_seat"
        unique_together = ("hold_id", "seat_id")
