
from django.forms import model_to_dict
from EventX.utils import paginate_queryset
from events.models import Events
from EventX.helper import BaseAPIClass
from events.serializers import FetchEventsSerializer, PostEventSerializer, PatchEventSerializer
from accounts.models import User
from django.db.models import Q


class EventView(BaseAPIClass):
    model_class = Events
    fetch_serializer = FetchEventsSerializer
    post_serializer = PostEventSerializer
    patch_serializer = PatchEventSerializer

    def get_event_by_id(self, event_id):
        return self.model_class.objects.get(events_id=event_id)

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

                events_objs = self.model_class.objects.filter(cond)
               
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
                self.error_occurred(serializer.errors)
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

                # Check if user is admin
                if user.user_type != User.USER_TYPE.ADMIN:
                    self.message = "Unauthorized Access"
                    self.error_occurred(e=None, custom_code=3104)
                    return self.get_response()
                
                # Create the event
                event = Events.objects.create(**serializer.validated_data)
                
                self.data = model_to_dict(event)
                self.message = "Event created successfully"
                
            else:
                self.custom_code = 3111
                self.error_occurred(serializer.errors)
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
                
                self.data = model_to_dict(event)
                self.message = "Event updated successfully"
                
            else:
                self.custom_code = 3121
                self.error_occurred(serializer.errors)
        except Exception as e:
            self.custom_code = 3122
            self.error_occurred(e)
        return self.get_response()