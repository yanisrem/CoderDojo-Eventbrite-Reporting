import pandas as pd

def extract_list_name_events(response):
    """
    Extracts a list of event names from a given response.

    Args:
        response (list): A list of dictionaries where each dictionary represents an event. 
                         Each event is expected to have a "name" key containing a dictionary 
                         with a "text" key.

    Returns:
        list: A list of strings representing the names of the events.
    
    Example:
        response = [
            {"name": {"text": "Event 1"}},
            {"name": {"text": "Event 2"}},
            {"name": {"text": "Event 3"}}
        ]
        result = extract_list_name_events(response)
        # result will be ["Event 1", "Event 2", "Event 3"]
    """
    list_name_events = [event["name"]["text"] for event in response]
    return list_name_events

def extract_event_informations(event):
    """
    Extracts relevant information from an Eventbrite event.

    Args:
        event (dict): A dictionary representing an event from the Eventbrite API response.

    Returns:
        dict: A dictionary containing the following event details:
            - "Name" (str): The name of the event.
            - "Event ID" (str): The unique identifier of the event.
            - "Description" (str): The description of the event.
            - "Url" (str): The URL link to the event.
            - "Creation Date" (str): The date when the event was created.
            - "Modification Date" (str): The date when the event was last modified.
            - "Publication Date" (str): The date when the event was published.
            - "Start Date" (str): The local start date and time of the event.
            - "End Date" (str): The local end date and time of the event.
            - "Capacity" (int or None): The capacity of the event (number of attendees allowed).
            - "Event Status" (str): The current status of the event (e.g., "live", "draft", "completed").

    Example:
        event_data = {
            "name": {"text": "Sample Event"},
            "description": {"text": "This is a sample event description."},
            "url": "https://eventbrite.com/sample-event",
            "created": "2024-06-01T12:00:00Z",
            "changed": "2024-06-05T15:00:00Z",
            "published": "2024-06-02T10:00:00Z",
            "start": {"local": "2024-06-10T09:00:00"},
            "end": {"local": "2024-06-10T17:00:00"},
            "capacity": 100,
            "status": "live",
            "id": "1234567890"
        }
        result = extract_event_informations(event_data)
        print(result)
        # Output:
        # {
        #   "Name": "Sample Event",
        #   "Event ID": "1234567890",
        #   "Description": "This is a sample event description.",
        #   "Url": "https://eventbrite.com/sample-event",
        #   "Creation Date": "2024-06-01T12:00:00Z",
        #   "Modification Date": "2024-06-05T15:00:00Z",
        #   "Publication Date": "2024-06-02T10:00:00Z",
        #   "Start Date": "2024-06-10T09:00:00",
        #   "End Date": "2024-06-10T17:00:00",
        #   "Capacity": 100,
        #   "Event Status": "live"
        # }
    """
    # Extract event details from the input dictionary
    if "name" in list(event.keys()):
        if "text" in list(event["name"].keys()):
            name = event["name"]["text"]
        else:
            name = pd.NA
    else:
        name = pd.NA
    if "description" in list(event.keys()):
        if "text" in list(event["description"].keys()):
            description = event["description"]["text"]
        else:
            description = pd.NA
    
    else:
        description = pd.NA
    url = event.get("url", pd.NA)
    created_date = event.get("created", pd.NA)
    changed_date = event.get("changed", pd.NA)
    published_date = event.get("published", pd.NA)
    if "start" in list(event.keys()):
        if "local" in list(event["start"].keys()):
            start_date = event["start"]["local"]
        else:
            start_date = pd.NA
    else:
        start_date = pd.NA
    if "end" in list(event.keys()):
        if "local" in list(event["end"].keys()):
            end_date = event["end"]["local"]
        else:
            end_date = pd.NA
    else:
        end_date = pd.NA
    capacity = event.get("capacity", pd.NA)
    status = event.get("status", pd.NA)
    id_event = event.get("id", pd.NA)

    # Build a dictionary with the extracted information
    dict_infos = {
        "Name": name,
        "Event ID": id_event,
        "Description": description,
        "Url": url,
        "Creation Date": created_date,
        "Modification Date": changed_date,
        "Publication Date": published_date,
        "Start Date": start_date,
        "End Date": end_date,
        "Capacity": capacity,
        "Event Status": status
    }
    return dict_infos


def extract_attendee_questions_answers(list_dict_questions_answers_attendee):
    """
    Extracts specific attendee details from a list of question-answer pairs provided for an attendee.

    Args:
        list_dict_questions_answers_attendee (list): A list of dictionaries, where each dictionary contains:
            - "question" (str): The question text.
            - "answer" (str): The answer provided for the question.

    Returns:
        dict: A dictionary containing the extracted attendee information with the following keys:
            - "Birth Date": The birth date of the attendee (if available).
            - "Age": The age of the attendee (if available).
            - "Postal Code": The postal code of the attendee (if available).
            - "Phone Number": The phone number of the attendee (if available).
            - "First Name Parent/Guardian": The first name of the parent or guardian (if available).
            - "Last Name Parent/Guardian": The last name of the parent or guardian (if available).

    Functionality:
        - Maps questions in various languages or formats to standardized attributes using a predefined mapping.
        - Matches each question with its corresponding attribute and updates the attendee information dictionary.

    Example:
        list_dict_questions_answers_attendee = [
            {"question": "Code postal", "answer": "12345"},
            {"question": "Geboortedatum", "answer": "01-01-2010"},
            {"question": "Voornaam (ouder/voogd)", "answer": "John"},
            {"question": "Achternaam (ouder/voogd)", "answer": "Doe"},
            {"question": "(GSM) in geval van een noodgeval", "answer": "123-456-7890"}
        ]
        result = extract_attendee_questions_answers(list_dict_questions_answers_attendee)
        # result will be:
        # {
        #     "Birth Date": "01-01-2010",
        #     "Age": pd.NA,
        #     "Postal Code": "12345",
        #     "Phone Number": "123-456-7890",
        #     "First Name Parent/Guardian": "John",
        #     "Last Name Parent/Guardian": "Doe"
        # }

    Notes:
        - Unmatched questions are ignored, and the corresponding attributes remain as `pd.NA`.
        - The function is case-sensitive to ensure accurate mapping.
    """
    dict_infos_attendee = {
        "Birth Date": pd.NA,
        "Age": pd.NA,
        "Postal Code": pd.NA,
        "Phone Number": pd.NA,
        "First Name Parent/Guardian": pd.NA,
        "Last Name Parent/Guardian": pd.NA
        }
    
    mapping_questions_answers = {
    "Code postal": "Postal Code", 
    "Postcode": "Postal Code", 
    "Code postal/Postcode/Postal Code": "Postal Code",
    
    "geboortedatum (dag-maand-jaar)": "Birth Date", 
    "Geboortedatum": "Birth Date", 
    "Geboortejaar": "Birth Date",
    
    "Âge": "Age", 
    "Age": "Age", 
    "Leeftijd": "Age", 
    "Age/Leeftijd": "Age", 
    "Leeftijd/Age": "Age", 
    "Leeftijd deelnemer": "Age", 
    "Voornaam, geslacht en leeftijd van iedereen die je inschrijft": "Age",
    
    "(GSM) in geval van een noodgeval": "Phone Number",
    "Coordonnées (en cas d'urgence uniquement)/Contact informatie (in geval van nood)/Contact information (in case of an emergency)": "Phone Number",
    "Coordonnées (en cas d'urgence uniquement)": "Phone Number", 
    "Contact informatie (in geval van nood)": "Phone Number", 
    "Voogd: GSM nummer": "Phone Number", 
    "Op welk telefoonnummer kunnen wij u bereiken tijdens de dojo?": "Phone Number",
    
    "Prénom (parent/tuteur)": "First Name Parent/Guardian", 
    "Voornaam (ouder/voogd)": "First Name Parent/Guardian", 
    "Voornaam (Ouder / Voogd)": "First Name Parent/Guardian", 
    "Voornaam en Achternaam(ouder/voogd)/Prénom et  Nom de famille(parent/tuteur)/First name and Last name(parent/guardian)": "First Name Parent/Guardian", 
    "Prénom (parent/tuteur·rice)": "First Name Parent/Guardian", 
    "Voornaam (ouder/voogd)/Prénom (parent/tuteur)/First name (parent/guardian)": "First Name Parent/Guardian", 
    "Prénom (parent/tuteur)/Voornaam (ouder/voogd)/First name (parent/guardian)": "First Name Parent/Guardian",
    
    "Nom de famille (parent/tuteur·rice)": "Last Name Parent/Guardian", 
    "Naam en voornaam (ouder/voogd)": "Last Name Parent/Guardian", 
    "Nom de famille (parent/tuteur)/Achternaam (ouder/voogd)/Surname (parent/guardian)": "Last Name Parent/Guardian", 
    "Achternaam (ouder/voogd)": "Last Name Parent/Guardian", 
    "Achternaam (ouder / voogd)": "Last Name Parent/Guardian", 
    "Achternaam (Ouder / Voogd)": "Last Name Parent/Guardian", 
    "Achternaam (ouder/voogd)/Nom de famille (parent/tuteur)/Surname (parent/guardian)": "Last Name Parent/Guardian", 
    "Naam van ouder/voogd": "Last Name Parent/Guardian", 
    "Nom de famille (parent/tuteur)": "Last Name Parent/Guardian", 
    "Naam ouder": "Last Name Parent/Guardian", 
    "Voogd: Voornaam en familienaam": "Last Name Parent/Guardian", 
    "Naam ouder:": "Last Name Parent/Guardian"
    }

    def match_question_answer(question, answer):
        attribute = mapping_questions_answers.get(question, pd.NA)
        if not pd.isna(attribute):
            dict_infos_attendee[attribute] = answer
    
    df_questions_answers = pd.DataFrame(list_dict_questions_answers_attendee)
    columns_df_questions_answers = list(df_questions_answers.columns)
    if ("question" in columns_df_questions_answers) and ("answer" in columns_df_questions_answers) :
        df_questions_answers.apply(lambda x: match_question_answer(x.question, x.answer), axis=1)
    
    return dict_infos_attendee


def extract_attendee_informations(list_dict_infos_attendees):
    """
    Extracts specific attendee information from a list of attendee dictionaries and organizes it into a DataFrame.

    Args:
        list_dict_infos_attendees (list): A list of dictionaries containing attendee information. Each dictionary
                                          includes details such as event ID, order ID, profile details, and custom answers.

    Returns:
        pd.DataFrame: A pandas DataFrame where each column represents a specific attendee detail:
            - "Event ID" (str or NA): The ID of the event.
            - "Order ID" (str or NA): The ID of the order.
            - "Order Date" (str or NA): The last modification date of the order.
            - "Ticket Type" (str or NA): The type of ticket purchased.
            - "Quantity" (int or NA): The number of tickets purchased.
            - "Attendee Status" (str or NA): The status of the attendee (e.g., "Attending").
            - "Last Name" (str or NA): The last name of the participant.
            - "First Name" (str or NA): The first name of the participant.
            - "Gender" (str or NA): The gender of the participant.
            - "Age" (str or NA): The age of the participant (from custom answers).
            - "Birth Date" (str or NA): The birth date of the participant (from custom answers).
            - "Email" (str or NA): The email address of the participant.
            - "Address" (dict or NA): The address of the participant.
            - "Postal Code" (str or NA): The postal code of the participant (from custom answers).
            - "Last Name Parent/Guardian" (str or NA): The last name of the participant's tutor (from custom answers).
            - "First Name Parent/Guardian" (str or NA): The first name of the participant's tutor (from custom answers).
            - "Phone Number" (str or NA): Emergency contact information.

    Raises:
        KeyError: If expected keys (like "profile" or "answers") are missing in an attendee dictionary.
        TypeError: If `dict_infos_attendees` is not a list.

    Example:
        attendees = [
            {
                "event_id": "12345",
                "order_id": "67890",
                "changed": "2024-06-10T12:00:00Z",
                "ticket_class_name": "VIP",
                "quantity": 2,
                "status": "Attending",
                "profile": {"last_name": "Doe", "first_name": "John", "gender": "Male", "email": "john.doe@example.com"},
                "answers": [
                    {"answer": "25"}, {"answer": "12345"}, {"answer": "Jane"}, {"answer": "Doe"},
                    {"answer": "123-456-7890"}, {"answer": "Yes"}, {"answer": "No"}
                ]
            }
        ]
        df = extract_attendee_informations(attendees)
        print(df)

    Notes:
        - Missing keys in the input dictionaries will result in `pd.NA` values for the corresponding fields.
        - The function assumes that the "answers" list contains answers in a specific order (e.g., age, postal code, etc.).
        - The function returns a pandas DataFrame for easy analysis and manipulation.
    """
    # Initialize the dictionary to hold attendee information
    if list_dict_infos_attendees == []:
        return []
    else:
        new_dict_infos_attendees = {
            "Event ID": [],
            "Order ID": [],
            "Order Date": [],
            "Ticket Type": [],
            "Quantity": [],
            "Attendee Status": [],
            "Last Name": [],
            "First Name": [],
            "Gender": [],
            "Age": [],
            "Birth Date": [],
            "Email": [],
            "Address": [],
            "City": [],
            "Postal Code": [],
            "Country": [],
            "Last Name Parent/Guardian": [],
            "First Name Parent/Guardian": [],
            "Phone Number": []
        }

        # Extract attendee information
        for dict_infos_attendee in list_dict_infos_attendees:
            # Extract values or use pd.NA if the key is missing
            event_id = dict_infos_attendee.get("event_id", pd.NA)
            order_id = dict_infos_attendee.get("order_id", pd.NA)
            order_date = dict_infos_attendee.get("changed", pd.NA)
            ticket_type = dict_infos_attendee.get("ticket_class_name", pd.NA)
            quantity = dict_infos_attendee.get("quantity", pd.NA)
            status = dict_infos_attendee.get("status", pd.NA)
            
            profile = dict_infos_attendee.get("profile", {})
            last_name = profile.get("last_name", pd.NA)
            first_name = profile.get("first_name", pd.NA)
            gender = profile.get("gender", pd.NA)
            email = profile.get("email", pd.NA)
            
            list_dict_questions_answers_attendee = dict_infos_attendee.get("answers",[])
            if list_dict_questions_answers_attendee == []: #No "answers"
                birth_date, age, postal_code, phone_number, first_name_tutor, last_name_tutor = pd.NA, pd.NA, pd.NA, pd.NA, pd.NA, pd.NA
            else:
                dict_question_answer = extract_attendee_questions_answers(list_dict_questions_answers_attendee)
                birth_date = dict_question_answer["Birth Date"]
                age = dict_question_answer["Age"]
                postal_code = dict_question_answer["Postal Code"]
                phone_number = dict_question_answer["Phone Number"]
                first_name_tutor = dict_question_answer["First Name Parent/Guardian"]
                last_name_tutor = dict_question_answer["Last Name Parent/Guardian"]
            
            addresses = profile.get("addresses", pd.NA)
            if addresses == {}:
                address, city, country = pd.NA, pd.NA, pd.NA
                 
            else:
                home_informations = addresses.get("home", {})
                city = home_informations.get("city", pd.NA)
                if pd.isna(postal_code):
                    postal_code = home_informations.get("postal_code", pd.NA)
                address = home_informations.get("address_1", pd.NA)
                country = home_informations.get("country", pd.NA)

            # Append values to the respective lists
            new_dict_infos_attendees["Event ID"].append(event_id)
            new_dict_infos_attendees["Order ID"].append(order_id)
            new_dict_infos_attendees["Order Date"].append(order_date)
            new_dict_infos_attendees["Ticket Type"].append(ticket_type)
            new_dict_infos_attendees["Quantity"].append(quantity)
            new_dict_infos_attendees["Attendee Status"].append(status)
            new_dict_infos_attendees["Last Name"].append(last_name)
            new_dict_infos_attendees["First Name"].append(first_name)
            new_dict_infos_attendees["Gender"].append(gender)
            new_dict_infos_attendees["Email"].append(email)
            new_dict_infos_attendees["Address"].append(address)

            new_dict_infos_attendees["Birth Date"].append(birth_date)
            new_dict_infos_attendees["Age"].append(age)
            new_dict_infos_attendees["Postal Code"].append(postal_code)
            new_dict_infos_attendees["City"].append(city)
            new_dict_infos_attendees["Country"].append(country)
            new_dict_infos_attendees["Phone Number"].append(phone_number)
            new_dict_infos_attendees["Last Name Parent/Guardian"].append(last_name_tutor)
            new_dict_infos_attendees["First Name Parent/Guardian"].append(first_name_tutor)
        
        return pd.DataFrame(new_dict_infos_attendees)