from django.urls import path
from analytics.views import AdminAnalyticsView

urlpatterns = [
    # Unified analytics endpoint with enum support
    path('', AdminAnalyticsView.as_view(), name='unified-analytics'),
]
