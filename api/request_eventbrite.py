import requests
from datetime import datetime

class RateLimitException(Exception):
    """Custom exception for rate limit errors (HTTP 429)."""
    pass

def get_filter_events_organization(token, start_date, end_date, id_organization="53624399466"):
    """
    Fetches events from the Eventbrite API for a specific organization.

    Args:
        token (str): The authentication token for the Eventbrite API.
        start_date (str): The start date for filtering events, in "YYYY-MM-DD" format.
        end_date (str): The end date for filtering events, in "YYYY-MM-DD" format.
        id_organization (str): The ID of the organization. Default is "53624399466".

    Returns:
        dict: The JSON response from the Eventbrite API containing event data.
    """ 
    # Helper function to validate date format
    def validate_date_format(date_str, param_name):
        try:
            if date_str:
                datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"The parameter '{param_name}' must be in 'YYYY-MM-DD' format.")

    # Validate date formats
    for date_param, param_name in [(start_date, "start_date"), (end_date, "end_date")]:
        validate_date_format(date_param, param_name)
    
    # Construct the API URL
    base_url = f"https://www.eventbriteapi.com/v3/organizations/{id_organization}/events/"
    params = {
        "order_by": "start_asc",
        "time_filter": "all",
        f"start_date.range_start": {start_date},
        f"start_date.range_end": {end_date},
        f"token": {token}}

    all_events = []
    page = 1 
    # Make the API request
    while True:
        try:
            params["page"] = page
            response = requests.get(base_url, params=params)
            
            if response.status_code == 429:  # Error 429: Rate limit exceeded
                raise RateLimitException("Hourly rate limit has been reached for this token. Default rate limits are 2,000 calls per hour.")
            elif response.status_code != 200:  # Other errors
                break
            
            data = response.json()
            all_events.extend(data.get("events", []))
            page += 1
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {e}")

    return all_events


def get_event_attendees(token, id_event):
    """
    Retrieves the list of attendees for a specific event from the Eventbrite API.

    Args:
        token (str): The authentication token for the Eventbrite API.
        id_event (str): The unique identifier of the event for which attendees are to be retrieved.

    Returns:
        list: A list of attendee information dictionaries. Each dictionary contains details about an attendee.

    Raises:
        Exception: If the API request fails due to network issues, invalid credentials, or other HTTP errors.

    Example:
        token = "your_api_token_here"
        id_event = "1234567890"

        try:
            attendees = get_event_attendees(token, id_event)
            print(attendees)
        except Exception as e:
            print(f"Error: {e}")

    Notes:
        - The function sends a GET request to the Eventbrite API endpoint for event attendees.
        - The API response must include a key "attendees", which contains the list of attendee details.
        - If the request fails (e.g., invalid token, event not found), an exception is raised with the error details.
    """
    # Construct the API URL
    base_url = f"https://www.eventbriteapi.com/v3/events/{id_event}/attendees/"

    params = {
        f"token": {token}}
    
    all_attendees = []
    page = 1 
    # Make the API request
    while True:
        try:
            params["page"] = page
            response = requests.get(base_url, params=params)
            
            if response.status_code == 429:
                raise RateLimitException("Hourly rate limit has been reached for this token. Default rate limits are 2,000 calls per hour.")
            elif response.status_code != 200:  # Other errors
                break
            
            data = response.json()
            all_attendees.extend(data.get("attendees", []))
            page += 1
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {e}")

    return all_attendees