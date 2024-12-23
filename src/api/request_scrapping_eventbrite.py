from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
import json
from selenium.webdriver.chrome.options import Options

def get_filter_events_organization(token, id_organization="53624399466", order_by="start_asc", time_filter="all", 
                                   start_date="", end_date="", created_start_date="", created_end_date=""):
    """
    Fetches events from the Eventbrite API for a specific organization.

    Args:
        token (str): The authentication token for the Eventbrite API.
        id_organization (str): The ID of the organization. Default is "53624399466".
        order_by (str): The sorting order of events ("start_asc", "start_desc", "created_asc", "created_desc", "name_asc", "name_desc"). Default is "start_asc".
        time_filter (str): The time filter to apply ("all", "past", "current_future"). Default is "all".
        start_date (str): The start date for filtering events, in "YYYY-MM-DD" format.
        end_date (str): The end date for filtering events, in "YYYY-MM-DD" format.
        created_start_date (str): The start date for filtering by event creation, in "YYYY-MM-DD" format.
        created_end_date (str): The end date for filtering by event creation, in "YYYY-MM-DD" format.

    Returns:
        dict: The JSON response from the Eventbrite API containing event data.

    Raises:
        ValueError: If the provided dates violate constraints based on the `time_filter` value:
            - For `time_filter="past"`, dates cannot be today or in the future.
            - For `time_filter="current_future"`, `end_date` cannot be strictly in the past.
        Exception: If the API request fails (e.g., network issues or invalid response).
    """
    # Get today's date
    today = datetime.now().date()
    
    # Helper function to validate date format
    def validate_date_format(date_str, param_name):
        try:
            if date_str:
                datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"The parameter '{param_name}' must be in 'YYYY-MM-DD' format.")

    # Validate date formats
    for date_param, param_name in [(start_date, "start_date"), (end_date, "end_date"), 
                                   (created_start_date, "created_start_date"), (created_end_date, "created_end_date")]:
        validate_date_format(date_param, param_name)
    
    # Enforce time_filter constraints
    if time_filter == "past":
        if (start_date and datetime.strptime(start_date, "%Y-%m-%d").date() >= today) or \
           (end_date and datetime.strptime(end_date, "%Y-%m-%d").date() >= today) or \
           (created_start_date and datetime.strptime(created_start_date, "%Y-%m-%d").date() >= today) or \
           (created_end_date and datetime.strptime(created_end_date, "%Y-%m-%d").date() >= today):
            raise ValueError("With time_filter='past', dates cannot be today or in the future.")
    
    if time_filter == "current_future":
        if end_date and datetime.strptime(end_date, "%Y-%m-%d").date() < today:
            raise ValueError("With time_filter='current_future', end_date cannot be strictly in the past.")
    
    # Construct the API URL
    url = f"https://www.eventbriteapi.com/v3/organizations/{id_organization}/events/?order_by={order_by}&time_filter={time_filter}"
    if start_date:
        url += f"&start_date.range_start={start_date}"
    if end_date:
        url += f"&start_date.range_end={end_date}"
    if created_start_date:
        url += f"&created_date.range_start={created_start_date}"
    if created_end_date:
        url += f"&created_date.range_end={created_end_date}"

    url += f"&token={token}"

    # Chrome driver
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)

    try:
        driver.get(url)
        list_json_data = list()

        while True:
            elements = driver.find_elements(By.CLASS_NAME, "language-json")
            if elements != []:
                json_data = json.loads(elements[0].text)
                list_json_data.append(json_data)
                # Tentez de cliquer sur le bouton "Next page" correspondant
                try:
                    # Trouvez toutes les divs avec la classe "pagination"
                    paginations = driver.find_elements(By.CLASS_NAME, "pagination")
                    
                    # Parcourez les divs pour trouver celle suivie par un <h4> avec le texte "Continuated response"
                    target_button = None
                    for pagination in paginations:
                        # Vérifiez si un <h4> avec le texte "Continuated response" suit cette div
                        h4_elements = pagination.find_elements(By.TAG_NAME, "h4")
                        if any(h4.text == "CONTINUATED RESPONSE" for h4 in h4_elements):
                            # Trouvez le bouton "Next page" dans cette div
                            target_button = pagination.find_element(By.CLASS_NAME, "next")
                            break
                    if target_button:
                        target_button.click()
                    else:
                        break #No Next page
                except NoSuchElementException:
                    driver.quit()
                    return [] #No page found in HMTL code
            else:
                driver.quit()
                return [] #No element
        driver.quit()
        return list_json_data

    except (TimeoutException, WebDriverException) as e:
        driver.quit()
        print(f"Connection or page loading error : {e}")
        return []


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
    url = f"https://www.eventbriteapi.com/v3/events/{id_event}/attendees/?token={token}"

    # Chrome driver
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)

    try:
        driver.get(url)
        list_json_data = list()

        while True:
            elements = driver.find_elements(By.CLASS_NAME, "language-json")
            if elements != []:
                json_data = json.loads(elements[0].text)
                list_json_data.append(json_data)
                try:
                    paginations = driver.find_elements(By.CLASS_NAME, "pagination")                
                    target_button = None
                    for pagination in paginations:
                        h4_elements = pagination.find_elements(By.TAG_NAME, "h4")
                        if any(h4.text == "CONTINUATED RESPONSE" for h4 in h4_elements):
                            target_button = pagination.find_element(By.CLASS_NAME, "next")
                            break
                    if target_button:
                        target_button.click()
                    else:
                        break #No next page
                except NoSuchElementException:
                    driver.quit()
                    return [] #No page found in HTML code
            else:
                driver.quit()
                return [] #No element
        driver.quit()
        return list_json_data
    
    except (TimeoutException, WebDriverException) as e:
        driver.quit()
        print(f"Connection or page loading error : {e}")