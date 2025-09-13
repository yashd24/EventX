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
    venue_id = serializers.IntegerField()
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    seat_mode = serializers.ChoiceField(choices=Events.SEAT_MODE.values)
    status = serializers.ChoiceField(choices=Events.EVENT_STATUS.values)
    sales_starts_at = serializers.DateTimeField()
    sales_ends_at = serializers.DateTimeField()

class PostEventSerializer(PostEventBaseSerializer):
    pass

class PatchEventSerializer(PostEventBaseSerializer):
    event_id = serializers.IntegerField()

