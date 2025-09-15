from enum import Enum
from rest_framework import serializers
from EventX.utils import validate_enum_str


class AnalyticsSerializer(serializers.Serializer):
    """ Serializer for all analytics types"""
    
    class ANALYTICS_TYPE(Enum):
        OVERVIEW = "overview"
        REVENUE = "revenue"
        EVENT_PERFORMANCE = "event_performance"

    analytics_type = serializers.ListField(child=serializers.CharField())
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    event_id = serializers.UUIDField(required=False)
    venue_id = serializers.UUIDField(required=False)
    group_by = serializers.ChoiceField(
        choices=['day', 'week', 'month'],
        default='day',
        required=False
    )

    def validate_analytics_type(self, value):
        return [validate_enum_str(item, self.ANALYTICS_TYPE) for item in value]
