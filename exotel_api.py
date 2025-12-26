import requests
import json
import os
import xml.etree.ElementTree as ET
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration - Load from environment variables
API_KEY = os.getenv("EXOTEL_API_KEY")
API_TOKEN = os.getenv("EXOTEL_API_TOKEN")
SUBDOMAIN = os.getenv("EXOTEL_SUBDOMAIN", "api.exotel.com")
SID = os.getenv("EXOTEL_SID")

# Base URL for Exotel API
BASE_URL = f"https://{API_KEY}:{API_TOKEN}@{SUBDOMAIN}/v1/Accounts/{SID}"

# Function to make an outbound call
def make_outbound_call(from_number, to_number, caller_id=None, call_type="trans"):
    """
    Make an outbound call using Exotel API
    
    Parameters:
    - from_number: Caller's number (from your Exotel account)
    - to_number: Recipient's phone number
    - caller_id: Optional caller ID
    - call_type: "trans" for transactional or "promo" for promotional
    """
    endpoint = f"{BASE_URL}/Calls"
    
    payload = {
        "From": from_number,
        "To": to_number,
        "CallerId": caller_id or from_number,
        "CallType": call_type
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    try:
        response = requests.post(
            endpoint,
            data=payload,
            headers=headers,
            auth=HTTPBasicAuth(API_KEY, API_TOKEN),
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 201:
            print("✓ Call initiated successfully!")
            return response.json()
        else:
            print("✗ Error making call")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None


# Function to get call details
def get_call_details(call_sid):
    """
    Get details of a specific call
    
    Parameters:
    - call_sid: The SID of the call
    """
    endpoint = f"{BASE_URL}/Calls/{call_sid}"
    
    try:
        response = requests.get(
            endpoint,
            auth=HTTPBasicAuth(API_KEY, API_TOKEN),
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        return response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None


# Function to get bulk call details
def get_bulk_call_details(page=1, limit=100):
    """
    Get bulk call details from Exotel API
    
    Parameters:
    - page: Page number (default: 1)
    - limit: Number of records to fetch (default: 100, max: 100)
    """
    endpoint = f"{BASE_URL}/Calls"
    
    params = {
        "PageSize": limit,
        "Page": page
    }
    
    try:
        response = requests.get(
            endpoint,
            params=params,
            auth=HTTPBasicAuth(API_KEY, API_TOKEN),
            timeout=30
        )
        
        if response.status_code == 200:
            # Parse XML response
            root = ET.fromstring(response.text)
            calls = []
            
            # Extract call data from XML
            for call_elem in root.findall('.//Call'):
                call_data = {}
                for child in call_elem:
                    call_data[child.tag] = child.text
                calls.append(call_data)
            
            # Extract metadata
            total = root.find('.//Total')
            page_size = root.find('.//PageSize')
            
            data = {
                "total": int(total.text) if total is not None else 0,
                "page_size": int(page_size.text) if page_size is not None else limit,
                "calls": calls
            }
            
            return data
        else:
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None
    except ET.ParseError as e:
        print(f"XML parse error: {e}")
        return None


# Function to get ALL bulk call details with pagination
def get_all_bulk_call_details(limit=100):
    """
    Get ALL bulk call details with automatic pagination (NO LIMIT)
    
    Parameters:
    - limit: Records per page (default: 100, max: 100)
    """
    all_calls = []
    page = 1
    seen_sids = set()
    
    print(f"[API] Starting to fetch all calls (no limit)...")
    
    while True:
        print(f"[API] Fetching page {page}...")
        
        data = get_bulk_call_details(page=page, limit=limit)
        
        if data is None:
            print(f"[API] Error on page {page}, stopping")
            break
        
        calls = data.get("calls", [])
        total = data.get("total", 0)
        
        print(f"[API] Page {page}: Got {len(calls)} calls (Total available: {total})")
        
        if not calls:
            print(f"[API] No more calls on page {page}, stopping")
            break
        
        # Add new calls, skip duplicates
        new_calls_count = 0
        for call in calls:
            sid = call.get("Sid")
            if sid and sid not in seen_sids:
                all_calls.append(call)
                seen_sids.add(sid)
                new_calls_count += 1
        
        print(f"[API] Added {new_calls_count} new unique calls (Total so far: {len(all_calls)})")
        
        # If we got 0 new calls, all are duplicates - stop pagination
        if new_calls_count == 0:
            print(f"[API] All calls on this page are duplicates, stopping pagination")
            break
        
        # Check if we've fetched all records
        if len(all_calls) >= total and total > 0:
            print(f"[API] All {total} calls fetched!")
            break
        
        page += 1
    
    print(f"[API] Fetch complete! Total unique calls: {len(all_calls)}")
    return all_calls


# Function to send SMS
def send_sms(to_number, message):
    """
    Send SMS using Exotel API
    
    Parameters:
    - to_number: Recipient's phone number
    - message: SMS message content
    """
    endpoint = f"{BASE_URL}/Sms/send"
    
    payload = {
        "To": to_number,
        "Body": message
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    try:
        response = requests.post(
            endpoint,
            data=payload,
            headers=headers,
            auth=HTTPBasicAuth(API_KEY, API_TOKEN),
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code in [200, 201]:
            print("✓ SMS sent successfully!")
            return response.json()
        else:
            print("✗ Error sending SMS")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None


# Main execution
if __name__ == "__main__":
    try:
        print("\n" + "="*80)
        print("EXOTEL API - FETCH ALL CALLS (NO LIMIT)")
        print("="*80 + "\n")
        
        # Fetch all call details
        all_calls = get_all_bulk_call_details()
        
        if all_calls:
            print(f"\n✓ Successfully fetched {len(all_calls)} calls\n")
            
            # Prepare data structure
            output_data = {
                "status": "success",
                "total_calls": len(all_calls),
                "timestamp": __import__('datetime').datetime.now().isoformat(),
                "calls": all_calls
            }
            
            # Save to JSON file
            output_filename = "call_details.json"
            with open(output_filename, "w") as json_file:
                json.dump(output_data, json_file, indent=2)
            
            print(f"✓ Saved to {output_filename}")
            print(f"✓ File size: {len(json.dumps(output_data, indent=2)) / 1024:.2f} KB")
        else:
            # Save error status
            print("\n✗ Failed to fetch calls\n")
            output_data = {
                "status": "error",
                "total_calls": 0,
                "timestamp": __import__('datetime').datetime.now().isoformat(),
                "error": "No calls fetched",
                "calls": []
            }
            
            output_filename = "call_details.json"
            with open(output_filename, "w") as json_file:
                json.dump(output_data, json_file, indent=2)
            
    except Exception as e:
        # Save error to JSON
        print(f"\n✗ Error: {e}\n")
        output_data = {
            "status": "error",
            "total_calls": 0,
            "timestamp": __import__('datetime').datetime.now().isoformat(),
            "error": str(e),
            "calls": []
        }
        
        output_filename = "call_details.json"
        with open(output_filename, "w") as json_file:
            json.dump(output_data, json_file, indent=2)
