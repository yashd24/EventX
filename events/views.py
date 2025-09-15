
from django.forms import model_to_dict
from EventX.utils import paginate_queryset
from EventX.cache_utils import cache_api_response, invalidate_events_cache
from events.models import Events, Venue
from EventX.helper import BaseAPIClass
from events.serializers import FetchEventsSerializer, PatchVenueSerializer, PostEventSerializer, PatchEventSerializer, PostVenueSerializer
from accounts.models import User
from django.db.models import Q


class EventView(BaseAPIClass):
    model_class = Events
    fetch_serializer = FetchEventsSerializer
    post_serializer = PostEventSerializer
    patch_serializer = PatchEventSerializer

    def get_event_by_id(self, event_id):
        return self.model_class.objects.get(events_id=event_id)

    @cache_api_response('events_list', timeout=180)  # 3 minutes cache
    def get(self, request):
        try:
            serializer = self.fetch_serializer(data=request.query_params)
            if serializer.is_valid():
                search = serializer.validated_data.get('search', '')
                page = serializer.validated_data.get('page', 1)
                rows_per_page = serializer.validated_data.get('rows_per_page', 10)

                cond = Q()

                if search:
                    cond |= Q(event_name__icontains=search)
                    cond |= Q(venue__city__icontains=search)
                    cond |= Q(venue__name__icontains=search)

                # Build query with select_related
                events_objs = self.model_class.objects.filter(cond).select_related('venue_id')
               
                # Paginate the queryset
                events_objs, total_count = paginate_queryset(events_objs, page, rows_per_page)
                events_objs = model_to_dict(events_objs)
                
                self.message = "Events fetched successfully"
                self.data = {
                    "events": events_objs,
                    "page": page,
                    "rows_per_page": rows_per_page,
                    "total_count": total_count
                }

            else:
                self.custom_code = 3101
                self.serializer_errors(serializer.errors)
        except Exception as e:
            self.custom_code = 3102
            self.error_occurred(e)
        return self.get_response()

    def post(self, request):
        try:
            # Get validated user from middleware
            user = request.validated_user
            serializer = self.post_serializer(data=request.data)
            
            if serializer.is_valid():

                venue_id = serializer.validated_data['venue_id']
                event_name = serializer.validated_data['event_name']
                starts_at = serializer.validated_data['starts_at']
                ends_at = serializer.validated_data['ends_at']
                seat_mode = serializer.validated_data['seat_mode']
                status = serializer.validated_data['status']
                sales_starts_at = serializer.validated_data['sales_starts_at']
                sales_ends_at = serializer.validated_data['sales_ends_at']

                print("Venue ID: ", venue_id, type(venue_id))

                # Check if user is admin
                if user.user_type != User.USER_TYPE.ADMIN:
                    self.message = "Unauthorized Access"
                    self.error_occurred(e=None, custom_code=3104)
                    return self.get_response()

                try:
                    venue = Venue.objects.get(venue_id=venue_id)
                    print(venue, type(venue))
                except Venue.DoesNotExist:
                    self.message = "Venue does not exist"
                    self.error_occurred(e=None, custom_code=3105)
                    return self.get_response()

                # Check if event already exists
                if Events.objects.filter(event_name=event_name).exists():
                    self.message = "Event already exists"
                    self.error_occurred(e=None, custom_code=3106)
                    return self.get_response()                
                
                # Create the event
                event = Events.objects.create(
                    venue_id=venue, 
                    event_name=event_name, 
                    starts_at=starts_at, 
                    ends_at=ends_at, 
                    seat_mode=seat_mode, 
                    status=status, 
                    sales_starts_at=sales_starts_at, 
                    sales_ends_at=sales_ends_at
                )
                
                # Invalidate events cache
                invalidate_events_cache(event_id=event.events_id, venue_id=venue.venue_id)
                
                self.data = model_to_dict(event)
                self.message = "Event created successfully"
                
            else:
                self.custom_code = 3111
                self.serializer_errors(serializer.errors)
        except Exception as e:
            self.custom_code = 3112
            self.error_occurred(e)
        return self.get_response()
    
    def patch(self, request):
        try:
            user = request.validated_user
            serializer = self.patch_serializer(data=request.data)
            if serializer.is_valid():

                # check if user is admin
                if user.user_type != User.USER_TYPE.ADMIN:
                    self.message = "Unauthorized Access"
                    self.error_occurred(e=None, custom_code=3104)
                    return self.get_response()
                
                event_id = serializer.validated_data['event_id']
                
                # get the event
                event = self.get_event_by_id(event_id)

                # update the event
                event.update(**serializer.validated_data)
                
                # Invalidate events cache
                invalidate_events_cache(event_id=event.events_id, venue_id=event.venue_id.venue_id)
                
                self.data = model_to_dict(event)
                self.message = "Event updated successfully"
                
            else:
                self.custom_code = 3121
                self.serializer_errors(serializer.errors)
        except Exception as e:
            self.custom_code = 3122
            self.error_occurred(e)
        return self.get_response()

class VenueView(BaseAPIClass):
    model_class = Venue
    post_serializer = PostVenueSerializer
    patch_serializer = PatchVenueSerializer

    def get_venue_by_id(self, venue_id):
        return self.model_class.objects.get(venue_id=venue_id)

    def post(self, request):
        try:
            user = request.validated_user
            serializer = self.post_serializer(data=request.data)
            if serializer.is_valid():
                name = serializer.validated_data['name']
                address = serializer.validated_data['address']
                city = serializer.validated_data['city']
                country = serializer.validated_data['country']
                capacity_hint = serializer.validated_data['capacity_hint']

                # Check if venue already exists
                if Venue.objects.filter(name=name).exists():
                    self.message = "Venue already exists"
                    self.error_occurred(e=None, custom_code=3133)
                    return self.get_response()

                
                venue = Venue.objects.create(**serializer.validated_data)
                self.data = {
                    "venue_id": str(venue.venue_id),
                    "name": venue.name,
                    "address": venue.address,
                    "city": venue.city,
                    "country": venue.country,
                    "capacity_hint": venue.capacity_hint,
                    "created_at": venue.created_at.isoformat()
                }
                self.message = "Venue created successfully"
            else:
                self.custom_code = 3131
                self.serializer_errors(serializer.errors)

        except Exception as e:
            self.custom_code = 3132
            self.error_occurred(e)
        return self.get_response()


    def patch(self, request):
        try:
            user = request.validated_user
            serializer = self.patch_serializer(data=request.data)
            if serializer.is_valid():
                venue_id = serializer.validated_data['venue_id']
                venue = self.get_venue_by_id(venue_id)
                venue.update(**serializer.validated_data)
                
                self.data = model_to_dict(venue)
                self.message = "Venue updated successfully"
            
            else:
                self.custom_code = 3141
                self.serializer_errors(serializer.errors)
        except Exception as e:
            self.custom_code = 3142
            self.error_occurred(e)
        return self.get_response()

