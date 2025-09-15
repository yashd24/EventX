from rest_framework import serializers

from EventX.utils import validate_enum_str
from events.models import Events


class SearchBaseSerializer(serializers.Serializer):
    search = serializers.CharField(max_length=500, required=False, min_length=1)

class PaginationBaseSerializer(SearchBaseSerializer):
    page = serializers.IntegerField(min_value=1, default=1)
    rows_per_page = serializers.IntegerField(default=10, min_value=10)

class FetchEventsSerializer(PaginationBaseSerializer):
    pass

class PostEventBaseSerializer(serializers.Serializer):
    event_name = serializers.CharField(max_length=255)
    venue_id = serializers.UUIDField()
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    seat_mode = serializers.CharField(max_length=20)
    status = serializers.CharField(max_length=20)
    sales_starts_at = serializers.DateTimeField()
    sales_ends_at = serializers.DateTimeField()

    def validate_seat_mode(self,value):
        return validate_enum_str(value, Events.SEAT_MODE)
    
    def validate_status(self,value):
        return validate_enum_str(value, Events.EVENT_STATUS)
    
    def validate(self, value):
        if value['starts_at'] >= value['ends_at'] or value['sales_starts_at'] >= value['sales_ends_at']:
            raise serializers.ValidationError("Start time must be before end time")
        return value

class PostEventSerializer(PostEventBaseSerializer):
    pass

class PatchEventSerializer(PostEventBaseSerializer):
    event_id = serializers.UUIDField()

class VenueBaseSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    address = serializers.CharField(max_length=255)
    city = serializers.CharField(max_length=255)
    country = serializers.CharField(max_length=255)
    capacity_hint = serializers.IntegerField()

class PostVenueSerializer(VenueBaseSerializer):
    pass

class PatchVenueSerializer(VenueBaseSerializer):
    venue_id = serializers.UUIDField()
