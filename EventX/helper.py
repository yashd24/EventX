from pickle import NONE
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from traceback import print_exc


class BaseAPIClass(APIView):
    """
    Base API class that provides common response handling methods
    for all API endpoints in the application.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.success = True
        self.message = None
        self.code = status.HTTP_200_OK
        self.custom_code = None
        self.exceptionObj = None
        self.data = {}
        self.print_log = True
    
    def get_response(self):
        """
        Generate a standardized success response
        """
        to_return = {
            "success": self.success, 
            "message": self.message if self.message else "Success", 
            "data": self.data, 
        }
        if self.custom_code:
            to_return["custom_code"] = self.custom_code
        
        if self.print_log:
            print("Response Debug Info:: ",self.exceptionObj)
            print("Return Object:: ",to_return)
        
        return Response(to_return, status=self.code,)
    
    def error_occurred(self, e, custom_code=None, **kwargs):
        """
        Generate a standardized error response
        """
        print_exc()  # This automatically prints the traceback to stderr
        self.success = False
        self.message = self.message if self.message else "Internal Server Error"
        self.code = status.HTTP_500_INTERNAL_SERVER_ERROR
        self.custom_code = custom_code if custom_code else self.custom_code
        self.data = kwargs
        self.exceptionObj = e

    def _process_error(self, key, value):
        """
        Process individual error items recursively
        """
        message = ""
        if isinstance(value, list):
            for item in value:
                # If the item is a dictionary or another list, process it recursively
                if isinstance(item, (list, dict)):
                    message += self._process_error(key, item)
                else:
                    message += f"{key} - {item}; "
        # If the value is a dictionary, recursively process it
        elif isinstance(value, dict):
            for sub_key, sub_value in value.items():
                if sub_key == "non_field_errors":
                    message += f"{key} - "
                message += self._process_error(sub_key, sub_value)
        else:
            # Handle the "non_field_errors" differently or any other key
            if key == "non_field_errors":
                message += value[0] + "; "
            else:
                message += key + " - " + value[0] + "; "
        return message

    def serializer_errors(self, errors):
        """
        Process serializer validation errors and format them into a readable message
        """
        message = ""
        
        print(errors)
        for key, value in errors.items():
            message += self._process_error(key, value)

        self.success = False
        self.message = message
        self.code = status.HTTP_400_BAD_REQUEST

