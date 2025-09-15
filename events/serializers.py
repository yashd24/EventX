from rest_framework import serializers

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
    seat_mode = serializers.ChoiceField(choices=Events.SEAT_MODE.values)
    status = serializers.ChoiceField(choices=Events.EVENT_STATUS.values)
    sales_starts_at = serializers.DateTimeField()
    sales_ends_at = serializers.DateTimeField()

class PostEventSerializer(PostEventBaseSerializer):
    
    def validate(self, value):
        if value['starts_at'] >= value['ends_at'] or value['sales_starts_at'] >= value['sales_ends_at']:
            raise serializers.ValidationError("Start time must be before end time")
        return value


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
