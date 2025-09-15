from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from django.utils import timezone
from datetime import timedelta
from EventX.helper import BaseAPIClass
from EventX.cache_utils import cache_api_response
from analytics.serializers import AnalyticsSerializer
from events.models import Events
from bookings.models import Booking, BookingItem
from inventory.models import EventInventory
from accounts.models import User


class AdminAnalyticsView(BaseAPIClass):
    """Main analytics view for admin dashboard"""
    serializer_class = AnalyticsSerializer

    @cache_api_response('unified_analytics', timeout=300)  # 5 minutes cache
    def get(self, request):
        """
        Get analytics data based on analytics_type enum
        Supported types: overview, revenue, event_performance
        """
        try:
            user = request.validated_user
            
            # Check if user is admin
            if user.user_type != User.USER_TYPE.ADMIN:
                self.message = "Admin access required"
                self.error_occurred(e=None, custom_code=5001)
                return self.get_response()
            
            serializer = self.serializer_class(data=request.GET)
            if serializer.is_valid():
                validated_data = serializer.validated_data
                analytics_type = validated_data['analytics_type']
                
                if self.serializer_class.ANALYTICS_TYPE.OVERVIEW in analytics_type:
                    self.data['overview'] = self._get_overview_analytics(validated_data)
                if self.serializer_class.ANALYTICS_TYPE.REVENUE in analytics_type:
                    self.data['revenue'] = self._get_revenue_analytics(validated_data)
                if self.serializer_class.ANALYTICS_TYPE.EVENT_PERFORMANCE in analytics_type:
                    self.data['event_performance'] = self._get_event_performance_analytics(validated_data)
                
                if not self.data:
                    self.message = "Invalid analytics type."
                    self.error_occurred(e=None, custom_code=5002)
                    return self.get_response()
            else:
                self.custom_code = 5003
                self._serializer_errors(serializer.errors)
                return self.get_response()
                
        except Exception as e:
            self.message = "Failed to retrieve analytics data"
            self.error_occurred(e, custom_code=5004)
            return self.get_response()

    def _get_overview_analytics(self, validated_data):
        """Get overview analytics"""
        start_date = validated_data.get('start_date')
        end_date = validated_data.get('end_date')
        event_id = validated_data.get('event_id')
        
        # Set default date range if not provided
        if not start_date:
            start_date = timezone.now().date() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now().date()
        
        # Build base queries
        bookings_query = Booking.objects.select_related('events_id', 'events_id__venue_id')
        events_query = Events.objects.select_related('venue_id')
        
        if start_date and end_date:
            bookings_query = bookings_query.filter(
                created_at__date__range=[start_date, end_date]
            )
        
        if event_id:
            bookings_query = bookings_query.filter(events_id=event_id)
            events_query = events_query.filter(events_id=event_id)
        
        # Calculate overview metrics
        booking_stats = bookings_query.aggregate(
            total_bookings=Count('booking_id'),
            confirmed_bookings=Count('booking_id', filter=Q(status=Booking.BOOKING_STATUS.CONFIRMED)),
            cancelled_bookings=Count('booking_id', filter=Q(status=Booking.BOOKING_STATUS.CANCELLED)),
            total_revenue=Sum('total_price_cents', filter=Q(status=Booking.BOOKING_STATUS.CONFIRMED)),
            avg_booking_value=Avg('total_price_cents', filter=Q(status=Booking.BOOKING_STATUS.CONFIRMED))
        )
        
        total_bookings = booking_stats['total_bookings']
        confirmed_bookings = booking_stats['confirmed_bookings']
        cancelled_bookings = booking_stats['cancelled_bookings']
        total_revenue = booking_stats['total_revenue'] or 0
        avg_booking_value = booking_stats['avg_booking_value'] or 0
        
        # Get event statistics
        event_stats = events_query.aggregate(
            total_events=Count('events_id'),
            active_events=Count('events_id', filter=Q(status=Events.EVENT_STATUS.PUBLISHED))
        )
        
        total_events = event_stats['total_events']
        active_events = event_stats['active_events']
        
        # Get top performing events
        top_events = bookings_query.filter(
            status=Booking.BOOKING_STATUS.CONFIRMED
        ).values(
            'events_id__event_name',
            'events_id__venue_id__name'
        ).annotate(
            booking_count=Count('booking_id'),
            total_revenue=Sum('total_price_cents')
        ).order_by('-total_revenue')[:5]
        
        # Get recent bookings
        recent_bookings = bookings_query.select_related(
            'events_id', 'events_id__venue_id', 'user'
        ).order_by('-created_at')[:10]
        
        # Calculate rates
        conversion_rate = (confirmed_bookings / total_bookings * 100) if total_bookings > 0 else 0
        cancellation_rate = (cancelled_bookings / total_bookings * 100) if total_bookings > 0 else 0
        
        data = {
            'summary': {
                'total_bookings': total_bookings,
                'confirmed_bookings': confirmed_bookings,
                'cancelled_bookings': cancelled_bookings,
                'total_revenue': total_revenue,
                'avg_booking_value': round(avg_booking_value, 2),
                'conversion_rate': round(conversion_rate, 2),
                'cancellation_rate': round(cancellation_rate, 2),
                'total_events': total_events,
                'active_events': active_events,
                'date_range': {
                    'start_date': start_date,
                    'end_date': end_date
                }
            },
            'top_events': list(top_events),
            'recent_bookings': [
                {
                    'booking_id': str(booking.booking_id),
                    'event_name': booking.events_id.event_name,
                    'venue_name': booking.events_id.venue_id.name,
                    'user_email': booking.user.email,
                    'total_amount': booking.total_price_cents,
                    'status': booking.status,
                    'created_at': booking.created_at
                }
                for booking in recent_bookings
            ]
        }

        return data

    def _get_revenue_analytics(self, validated_data):
        """Get revenue analytics"""
        start_date = validated_data.get('start_date')
        end_date = validated_data.get('end_date')
        event_id = validated_data.get('event_id')
        group_by = validated_data.get('group_by', 'day')
        
        # Set default date range
        if not start_date:
            start_date = timezone.now().date() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now().date()
        
        # Build query
        bookings_query = Booking.objects.filter(
            created_at__date__range=[start_date, end_date],
            status=Booking.BOOKING_STATUS.CONFIRMED
        )
        
        if event_id:
            bookings_query = bookings_query.filter(events_id=event_id)
        
        # Calculate total revenue
        total_revenue = bookings_query.aggregate(
            total=Sum('total_price_cents')
        )['total'] or 0
        
        # Revenue by event
        revenue_by_event = bookings_query.values(
            'events_id__event_name'
        ).annotate(
            revenue=Sum('total_price_cents'),
            booking_count=Count('booking_id')
        ).order_by('-revenue')
        
        # Revenue by ticket type
        revenue_by_ticket_type = BookingItem.objects.filter(
            booking_id__in=bookings_query
        ).values(
            'ticket_type_id__ticket_type_name'
        ).annotate(
            revenue=Sum('total_price'),
            quantity=Sum('quantity')
        ).order_by('-revenue')
        
        # Revenue trends by time period
        if group_by == 'day':
            trunc_func = TruncDate('created_at')
        elif group_by == 'week':
            trunc_func = TruncWeek('created_at')
        elif group_by == 'month':
            trunc_func = TruncMonth('created_at')
        else:
            trunc_func = TruncDate('created_at')
        
        revenue_trends = bookings_query.annotate(
            period=trunc_func
        ).values('period').annotate(
            revenue=Sum('total_price_cents'),
            booking_count=Count('booking_id')
        ).order_by('period')
        
        data = {
            'summary': {
                'total_revenue': total_revenue,
                'total_bookings': bookings_query.count(),
                'average_booking_value': total_revenue / bookings_query.count() if bookings_query.count() > 0 else 0,
                'date_range': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'group_by': group_by
            },
            'revenue_by_event': list(revenue_by_event),
            'revenue_by_ticket_type': list(revenue_by_ticket_type),
            'revenue_trends': list(revenue_trends)
        }

        return data

    def _get_event_performance_analytics(self, validated_data):
        """Get event performance analytics"""
        start_date = validated_data.get('start_date')
        end_date = validated_data.get('end_date')
        event_id = validated_data.get('event_id')
        
        # Set default date range
        if not start_date:
            start_date = timezone.now().date() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now().date()
        
        # Get event performance data
        events_query = Events.objects.filter(
            event_date__date__range=[start_date, end_date]
        ).select_related('venue_id')
        
        if event_id:
            events_query = events_query.filter(events_id=event_id)
        
        event_performance = []
        for event in events_query:
            bookings = Booking.objects.filter(events_id=event)
            booking_count = bookings.count()
            confirmed_bookings = bookings.filter(status=Booking.BOOKING_STATUS.CONFIRMED).count()
            total_revenue = bookings.filter(status=Booking.BOOKING_STATUS.CONFIRMED).aggregate(
                total=Sum('total_price_cents')
            )['total'] or 0
            
            # Get capacity utilization
            total_capacity = 0
            if event.seat_mode == Events.SEAT_MODE.GENERAL_ADMISSION:
                inventories = EventInventory.objects.filter(event_id=event)
                total_capacity = sum(inv.initial_qty for inv in inventories)
            elif event.seat_mode == Events.SEAT_MODE.RESERVED_SEATING:
                total_capacity = event.seats.count()
            
            utilization_rate = (confirmed_bookings / total_capacity * 100) if total_capacity > 0 else 0
            
            # Calculate conversion rate for this event
            conversion_rate = (confirmed_bookings / booking_count * 100) if booking_count > 0 else 0
            
            event_performance.append({
                'event_id': str(event.events_id),
                'event_name': event.event_name,
                'event_date': event.event_date,
                'venue_name': event.venue_id.name,
                'seat_mode': event.seat_mode,
                'status': event.status,
                'total_bookings': booking_count,
                'confirmed_bookings': confirmed_bookings,
                'total_revenue': total_revenue,
                'total_capacity': total_capacity,
                'utilization_rate': round(utilization_rate, 2),
                'conversion_rate': round(conversion_rate, 2)
            })
        
        # Sort by revenue
        event_performance.sort(key=lambda x: x['total_revenue'], reverse=True)
        
        data = {
            'events': event_performance,
            'summary': {
                'total_events': len(event_performance),
                'total_revenue': sum(event['total_revenue'] for event in event_performance),
                'average_utilization': sum(event['utilization_rate'] for event in event_performance) / len(event_performance) if event_performance else 0,
                'average_conversion': sum(event['conversion_rate'] for event in event_performance) / len(event_performance) if event_performance else 0,
                'date_range': {
                    'start_date': start_date,
                    'end_date': end_date
                }
            }
        }

        return data
