#!/usr/bin/env python
"""
Test script for the booking system
"""
import os
import sys
import django
from datetime import datetime, timedelta
import requests
import json

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'EventX.settings')
django.setup()

from accounts.models import User
from events.models import Events, Venue, TicketType
from inventory.models import EventInventory, Seat
from bookings.models import Booking

def create_test_data():
    """Create test data for booking system"""
    print("Creating test data...")
    
    # Create test venue
    venue, created = Venue.objects.get_or_create(
        name="Test Arena",
        defaults={
            'address': "123 Test Street",
            'city': "Test City",
            'country': "Test Country",
            'capacity_hint': 1000
        }
    )
    print(f"Venue: {venue.name} (ID: {venue.venue_id})")
    
    # Create test event
    event, created = Events.objects.get_or_create(
        event_name="Test Concert",
        defaults={
            'venue_id': venue,
            'starts_at': datetime.now() + timedelta(days=30),
            'ends_at': datetime.now() + timedelta(days=30, hours=3),
            'seat_mode': Events.SEAT_MODE.GENERAL_ADMISSION,
            'status': Events.EVENT_STATUS.PUBLISHED,
            'sales_starts_at': datetime.now() - timedelta(days=1),
            'sales_ends_at': datetime.now() + timedelta(days=29)
        }
    )
    print(f"Event: {event.event_name} (ID: {event.events_id})")
    
    # Create ticket type
    ticket_type, created = TicketType.objects.get_or_create(
        events_id=event,
        ticket_type_name="General Admission",
        defaults={
            'price': 5000,  # $50.00 in cents
            'currency': 'USD',
            'is_active': True
        }
    )
    print(f"Ticket Type: {ticket_type.ticket_type_name} (ID: {ticket_type.ticket_type_id})")
    
    # Create event inventory
    inventory, created = EventInventory.objects.get_or_create(
        event_id=event,
        ticket_type_id=ticket_type,
        defaults={
            'initial_qty': 100,
            'sold_qty': 0,
            'held_qty': 0
        }
    )
    print(f"Inventory: {inventory.initial_qty} tickets available")
    
    # Create test user
    user, created = User.objects.get_or_create(
        email="test@example.com",
        defaults={
            'name': "Test User",
            'user_type': User.USER_TYPE.USER
        }
    )
    if created:
        user.set_password("testpassword123")
        user.save()
    print(f"User: {user.email} (ID: {user.user_id})")
    
    return {
        'venue': venue,
        'event': event,
        'ticket_type': ticket_type,
        'inventory': inventory,
        'user': user
    }

def test_booking_api():
    """Test the booking API endpoints"""
    print("\n" + "="*50)
    print("TESTING BOOKING API ENDPOINTS")
    print("="*50)
    
    base_url = "http://127.0.0.1:8000"
    
    # Test data
    test_data = create_test_data()
    
    # Step 1: Login to get access token
    print("\n1. Testing Login...")
    login_data = {
        "email": "test@example.com",
        "password": "testpassword123"
    }
    
    try:
        response = requests.post(f"{base_url}/accounts/login/", json=login_data)
        print(f"Login Status: {response.status_code}")
        
        if response.status_code == 200:
            login_result = response.json()
            if login_result.get('success'):
                access_token = login_result['data']['access_token']
                print(f"✅ Login successful! Token: {access_token[:20]}...")
                
                headers = {
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                }
                
                # Step 2: Test booking creation
                print("\n2. Testing Booking Creation...")
                booking_data = {
                    "event_id": str(test_data['event'].events_id),
                    "ticket_type_id": str(test_data['ticket_type'].ticket_type_id),
                    "quantity": 2
                }
                
                response = requests.post(f"{base_url}/bookings/", json=booking_data, headers=headers)
                print(f"Booking Creation Status: {response.status_code}")
                print(f"Response: {json.dumps(response.json(), indent=2)}")
                
                if response.status_code == 200:
                    booking_result = response.json()
                    if booking_result.get('success'):
                        booking_id = booking_result['data']['booking_id']
                        print(f"✅ Booking created successfully! ID: {booking_id}")
                        
                        # Step 3: Test booking history
                        print("\n3. Testing Booking History...")
                        response = requests.get(f"{base_url}/bookings/", headers=headers)
                        print(f"Booking History Status: {response.status_code}")
                        print(f"Response: {json.dumps(response.json(), indent=2)}")
                        
                        # Step 4: Test booking cancellation
                        print("\n4. Testing Booking Cancellation...")
                        response = requests.delete(f"{base_url}/bookings/{booking_id}/", headers=headers)
                        print(f"Booking Cancellation Status: {response.status_code}")
                        print(f"Response: {json.dumps(response.json(), indent=2)}")
                        
                        if response.status_code == 200:
                            print("✅ Booking cancelled successfully!")
                        else:
                            print("❌ Booking cancellation failed!")
                    else:
                        print("❌ Booking creation failed!")
                else:
                    print("❌ Booking creation failed!")
            else:
                print("❌ Login failed!")
        else:
            print("❌ Login failed!")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure Django server is running on http://127.0.0.1:8000")
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")

def test_concurrency():
    """Test concurrent booking requests"""
    print("\n" + "="*50)
    print("TESTING CONCURRENCY")
    print("="*50)
    
    # This would require threading/multiprocessing to test properly
    # For now, just show the concept
    print("Concurrency testing would require:")
    print("1. Multiple simultaneous requests")
    print("2. Threading or async requests")
    print("3. Verification that no overselling occurs")
    print("4. Database transaction rollback testing")

if __name__ == "__main__":
    print("🚀 Starting Booking System Tests...")
    
    # Create test data
    test_data = create_test_data()
    
    # Test API endpoints
    test_booking_api()
    
    # Show concurrency testing info
    test_concurrency()
    
    print("\n" + "="*50)
    print("TESTING COMPLETE")
    print("="*50)
