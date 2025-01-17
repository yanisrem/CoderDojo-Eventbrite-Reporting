import requests
import sys
import os
import pandas as pd
import geopandas as gpd
pd.options.mode.chained_assignment = None  # default='warn'
import numpy as np
import re #native
import unicodedata #native
import dash
from dash import dcc, html, Input, Output, State, dash_table, DiskcacheManager, CeleryManager
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from concurrent.futures import ThreadPoolExecutor
import plotly.express as px
import pgeocode
from controler.auth_page import auth_page
from controler.main_page import main_page
from api.request_eventbrite import get_filter_events_organization, get_location_event, get_event_attendees, RateLimitException
from services.events import extract_event_informations, extract_attendee_informations, extract_list_name_events

# Init Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
app.title = "Eventbrite App"
server = app.server

# Layouts
app.layout = dbc.Container([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='token-store'),
    html.Div(id='page-content'),
    html.Div(id='event-details'),  # Container for displaying the event details table
    html.Div(id='error-message', style={'color': 'red'})  # For displaying error messages
], fluid=True)

# Callback for pages navigation
@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname):
    if pathname == '/main':
        return main_page()
    return auth_page()

# Callback to check token
@app.callback(
    [Output('url', 'pathname'),
     Output('error-message', 'children'),
     Output('token-store', 'data')],  # Store token
    Input('submit-button', 'n_clicks'),
    State('token-input', 'value')
)
def authenticate(n_clicks, token):
    if n_clicks == 0:
        raise PreventUpdate

    url = 'https://www.eventbriteapi.com/v3/users/me/'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            # Valid token
            return '/main', '', token
        elif response.status_code == 429:
            # Rate Limit
            return dash.no_update, "Hourly rate limit has been reached for this token", None
        else:
            # Invalid token
            return dash.no_update, "Invalid token", None
    except Exception as e:
        return dash.no_update, "An error occurred. Please try again.", None


# Callback to filter events
@app.callback(
    Output('event-list', 'children'),
    Input('filter-button', 'n_clicks'),
    State('start-date-picker', 'date'),
    State('end-date-picker', 'date'),
    State('token-store', 'data')  # Get stored token
)

def filter_events(n_clicks, start_date, end_date, token):
    if n_clicks == 0:
        raise PreventUpdate

    if not start_date or not end_date:
        return html.Div("Please select both start and end dates.", style={'color': 'red'})

    if start_date > end_date:
        return html.Div("Start date cannot be greater than end date.", style={'color': 'red'})

    if not token:
        return html.Div("Token not found. Please log in again.", style={'color': 'red'})

    try:
        events = get_filter_events_organization(token=token,
                                                start_date=start_date,
                                                end_date=end_date)
        event_names = extract_list_name_events(events)
        options = [{'label': name, 'value': name} for name in event_names]
        options.insert(0, {'label': 'All', 'value': 'All'})  # "All" option
        return dbc.Card([
            dbc.CardBody([
                dcc.Checklist(
                    options=options,
                    id='event-selector',
                    value=[],
                    labelStyle={'display': 'block', 'textAlign': 'left'}
                ),
                dbc.Button("Validate", id='validate-button', n_clicks=0, color="primary", className="mt-3")
            ])
        ])
    except RateLimitException as e:
        return html.Div(str(e), style={'color': 'red'})
    except Exception as e:
        return html.Div(f"An error occurred: {str(e)}", style={'color': 'red'})


# Callback to manage "All" selection
@app.callback(
    Output('event-selector', 'value'),
    Input('event-selector', 'value'),
    State('event-selector', 'options')
)
def select_all_events(selected_values, options):
    all_values = [option['value'] for option in options if option['value'] != 'All']
    if 'All' in selected_values:
        if set(all_values).issubset(selected_values):
            return []
        else:
            return all_values
    return selected_values

# Display selected events and attendees
def display_selected_events(selected_event_names, token, start_date, end_date):
    if not selected_event_names or not token:
        return html.Div("No events selected or token missing.", style={'color': 'red'})

    try:
        response = get_filter_events_organization(token=token,
                                                  start_date=start_date,
                                                  end_date=end_date)
        selected_events = [
            event for event in response
            if event["name"]["text"] in selected_event_names
        ]

        # Extract events' informations
        list_event_infos = [extract_event_informations(event) for event in selected_events]
        df_event_infos = pd.DataFrame(list_event_infos)

        # Extract events' location informations
        list_dict_address = [get_location_event(token, venue_id) for venue_id in df_event_infos["Venue ID"]]
        #df_addresses_events.columns = ["address_1", "address_2", "city", ..., "postal_code", ...]
        df_addresses_events = pd.DataFrame(list_dict_address)
        list_postal_code_events = df_addresses_events["postal_code"].tolist()

        nomi = pgeocode.Nominatim('be')
        df_event_location_infos = nomi.query_postal_code(list_postal_code_events)
        df_event_location_infos = df_event_location_infos[["place_name", "postal_code", "county_name", "state_name"]]
        df_event_location_infos.rename(columns={"place_name": "Dojo City",
                                        "postal_code": "Dojo Postal Code",
                                        "county_name": "Dojo Province",
                                        "state_name": "Dojo Region" #Brussel, Wallonie, Flanders
                                        }, inplace=True)
        df_event_location_infos['Dojo Region'] = df_event_location_infos['Dojo Region'].replace('Bruxelles-Capitale','Brussels')
        df_event_location_infos['Dojo Region'] = df_event_location_infos['Dojo Region'].replace('Vlaanderen','Flanders')
        df_event_location_infos['Dojo Region'] = df_event_location_infos['Dojo Region'].replace('Wallonie','Wallonia')
    
        df_event_infos.drop(columns=["Venue ID"], inplace=True)
        df_event_infos = pd.concat([df_event_infos, df_event_location_infos], axis=1)
    
        # Extract attendees' informations
        def fetch_attendee_data(event_id):
            """Fetch and process attendee data for a single event."""
            attendees_data = get_event_attendees(token, event_id)
            return extract_attendee_informations(attendees_data)

        with ThreadPoolExecutor() as executor:
            list_df_infos_attendees_per_event = list(
                executor.map(fetch_attendee_data, df_event_infos["Event ID"])
            )

        filtered_list_df_infos_attendees_per_event = [item for item in list_df_infos_attendees_per_event if not isinstance(item, list)]
        df_infos_attendees_per_event = pd.concat(filtered_list_df_infos_attendees_per_event, axis=0, ignore_index=True)

        df_infos_events_and_attendees = pd.merge(
            df_event_infos, 
            df_infos_attendees_per_event, 
            how='left', 
            on=["Event ID"]
        )

        def clean_string(string):
            if string is pd.NA:
                return string
            else:
                try:
                    string = str(string)
                    string_without_accent = unicodedata.normalize('NFD', string).encode('ascii', 'ignore').decode('utf-8')
                    filtered_sting = re.sub(r'[^a-zA-Z]', '', string_without_accent).lower()
                    return filtered_sting
                except:
                    return string

        df_infos_events_and_attendees["Clean Ticket Type"] = df_infos_events_and_attendees["Ticket Type"].apply(clean_string)
        if getattr(sys, 'frozen', False):
            # Executable
            application_path = sys._MEIPASS
        else:
            # Developement
            application_path = os.path.dirname(__file__)
        csv_path = os.path.join(application_path, 'assets', 'clean_ticket.csv')
        df_ticket = pd.read_csv(csv_path, sep=",", index_col=0)
        #One new column from df_ticket "Ticket Category": Participant, Volunteer or Other
        df_infos_events_and_attendees = pd.merge(
            df_infos_events_and_attendees,
            df_ticket,
            how='left',
            on=["Clean Ticket Type"]
        )
        df_infos_events_and_attendees.drop(columns=['Clean Ticket Type'], inplace=True)
        columns = [
            'Name', 'Event ID', 'Dojo City', 'Dojo Postal Code', 'Dojo Province',
            'Dojo Region', 'Start Date', 'End Date', 'Capacity', 'Event Status', 
            'Order ID', 'Order Date', 'Ticket Type', 'Ticket Category', 'Quantity', 
            'Attendee Status', 'Last Name', 'First Name', 'Gender', 'Age', 'Birth Date', 
            'Email', 'Address', 'City', 'Postal Code', 'Country', 'Last Name Parent/Guardian', 
            'First Name Parent/Guardian', 'Phone Number']
        df_infos_events_and_attendees = df_infos_events_and_attendees[columns]
        df_infos_events_and_attendees_participants = df_infos_events_and_attendees.loc[df_infos_events_and_attendees["Ticket Category"] == "Participant"]
        df_infos_events_and_attendees_participants = df_infos_events_and_attendees_participants.loc[df_infos_events_and_attendees_participants["Attendee Status"] == "Checked In"]
        df_infos_events_and_attendees_volunteers = df_infos_events_and_attendees.loc[df_infos_events_and_attendees["Ticket Category"] == "Volunteer"]
        df_infos_events_and_attendees_volunteers = df_infos_events_and_attendees_volunteers.loc[df_infos_events_and_attendees_volunteers["Attendee Status"] == "Checked In"]

        # Age barplot - Participants
        bins = [-1, 3, 6, 9, 12, 15, 18, np.inf] # [-1, 2], [3, 5], [6, 8], [9,11], [12, 14], [15, 17], [18, +]
        names = ['Missing', '3-5', '6-8', '9-11', '12-14', '15-17', '17>']

        ## Replace pd.NA by -1 to avoid error in pd.cut()
        df_infos_events_and_attendees_participants['AgeFilled'] = df_infos_events_and_attendees_participants['Age'].fillna(-1)
        df_infos_events_and_attendees_participants['AgeRange'] = pd.cut(df_infos_events_and_attendees_participants['AgeFilled'],
                                                                        bins=bins,
                                                                        labels=names,
                                                                        right=False)
        
        df_infos_events_and_attendees_participants.drop(columns=['AgeFilled'], inplace=True)        
        age_category_counts = df_infos_events_and_attendees_participants['AgeRange'].value_counts(normalize=True).reset_index()
        age_category_counts.columns = ['Age', 'Frequency']
        age_category_counts['Age'] = pd.Categorical(age_category_counts['Age'], categories=names, ordered=True)
        age_category_counts = age_category_counts.sort_values('Age')
        age_category_counts['Frequency'] = age_category_counts['Frequency'] * 100
        age_barplot_participants = px.bar(
            age_category_counts,
            x='Age', y='Frequency',
            title="Age Distribution of Checked In Participants",
            labels={'Age': 'Age', 'Frequency': 'Frequency (in %)'},
            color='Age',
            color_continuous_scale='Viridis'
        )
        age_barplot_participants.update_layout(showlegend=False)

        # Gender barplot - Participants
        gender_category_counts = df_infos_events_and_attendees_participants['Gender'].value_counts(normalize=True).reset_index()
        gender_category_counts.columns = ["Gender", "Frequency"]
        gender_category_counts['Frequency'] = gender_category_counts['Frequency'] * 100
        gender_barplot_participants = px.bar(
            gender_category_counts,
            x='Gender', y='Frequency',
            title="Checked In Participants by Gender",
            labels={'Gender': 'Gender', 'Frequency': 'Frequency (in %)'},
            color='Gender',
            color_discrete_map={'male': 'blue', 'female': 'pink'}
        )

        # Age barplot - Volunteers
        bins = [-1, 0, 16, 22, 31, 41, 51, 61, 71, np.inf] # [-1, -1], [0, 15], [16, 21], [22,30], [31, 40], [41, 50], [51, 60], [61, 70], 70>
        names = ['Missing', '<16', '16-21', '22-30', '31-40', '41-50', '51-60', '61-70', '70>']
        ## Replace pd.NA by -1 to avoid error in pd.cut()
        df_infos_events_and_attendees_volunteers['AgeFilled'] = df_infos_events_and_attendees_volunteers['Age'].fillna(-1)
        df_infos_events_and_attendees_volunteers['AgeRange'] = pd.cut(df_infos_events_and_attendees_volunteers['AgeFilled'],
                                                                        bins=bins,
                                                                        labels=names,
                                                                        right=False)
        
        df_infos_events_and_attendees_volunteers.drop(columns=['AgeFilled'], inplace=True)        
        age_category_counts = df_infos_events_and_attendees_volunteers['AgeRange'].value_counts(normalize=True).reset_index()
        age_category_counts.columns = ['Age', 'Frequency']
        age_category_counts['Age'] = pd.Categorical(age_category_counts['Age'], categories=names, ordered=True)
        age_category_counts = age_category_counts.sort_values('Age')
        age_category_counts['Frequency'] = age_category_counts['Frequency'] * 100
        age_barplot_volunteers = px.bar(
            age_category_counts,
            x='Age', y='Frequency',
            title="Age Distribution of Checked In Volunteers",
            labels={'Age': 'Age', 'Frequency': 'Frequency (in %)'},
            color='Age',
            color_continuous_scale='Viridis'
        )
        age_barplot_volunteers.update_layout(showlegend=False)

        # Gender barplot - Volunteers
        gender_category_counts = df_infos_events_and_attendees_volunteers['Gender'].value_counts(normalize=True).reset_index()
        gender_category_counts.columns = ["Gender", "Frequency"]
        gender_category_counts['Frequency'] = gender_category_counts['Frequency'] * 100
        gender_barplot_volunteers = px.bar(
            gender_category_counts,
            x='Gender', y='Frequency',
            title="Checked In Volunteers by Gender",
            labels={'Gender': 'Gender', 'Frequency': 'Frequency (in %)'},
            color='Gender',
            color_discrete_map={'male': 'blue', 'female': 'pink'}
        )

        # Dojo frequency, Dojo participant, Dojo volunteers per region
        ## Among dojos, number of times "Flanders" appears (bc one row = one dojo)
        df_dojo_freq_by_region = df_event_infos['Dojo Region'].value_counts().reset_index()
        df_dojo_freq_by_region.columns = ["Region", "Number of Dojos per Region"]
        
        ## Among participants, number of times "Flanders" appears (bc one row = one participant)
        df_participant_freq_by_region = df_infos_events_and_attendees_participants['Dojo Region'].value_counts().reset_index()
        df_participant_freq_by_region.columns = ["Region", "Number of Participants per Region"]

        ## Among volunteers, number of times "Flanders" appears (bc one row = one participant)
        df_volunteers_freq_by_region = df_infos_events_and_attendees_volunteers['Dojo Region'].value_counts().reset_index()
        df_volunteers_freq_by_region.columns = ["Region", "Number of Volunteers per Region"]

        ## Merge three Dataframes
        df_freq_by_region = df_dojo_freq_by_region.merge(df_participant_freq_by_region,on='Region').merge(df_volunteers_freq_by_region,on='Region')

        ## Import geopandas data
        json_path = os.path.join(application_path, 'assets', 'be.json')
        belgium_regions = gpd.read_file(json_path)
        belgium_regions = belgium_regions.rename(columns={"name": "Region"})

        ## Merge geopandas data with regions frequency
        merged_freq_region = belgium_regions.merge(df_freq_by_region, on="Region")
        geojson_data = merged_freq_region.__geo_interface__

        ## Graph dojo frequency by region
        fig_dojo_freq = px.choropleth_mapbox(
        merged_freq_region,
        geojson=geojson_data,
        locations=merged_freq_region.index,
        color="Number of Dojos per Region",
        color_continuous_scale="OrRd",
        mapbox_style="carto-positron",
        center={"lat": 50.5, "lon": 4.5},
        zoom=6,
        opacity=0.7,
        labels={"Number of Dojos per Region": ""})

        fig_dojo_freq.update_layout(title="Number of Dojos per Region")

        ## Graph participant frequency by region
        fig_participant_freq = px.choropleth_mapbox(
        merged_freq_region,
        geojson=geojson_data,
        locations=merged_freq_region.index,
        color="Number of Participants per Region",
        color_continuous_scale="OrRd",
        mapbox_style="carto-positron",
        center={"lat": 50.5, "lon": 4.5},
        zoom=6,
        opacity=0.7,
        labels={"Number of Participants per Region": ""})

        fig_participant_freq.update_layout(title="Number of Checked In Participants per Region")

        ## Graph volunteers frequency by region
        fig_volunteers_freq = px.choropleth_mapbox(
        merged_freq_region,
        geojson=geojson_data,
        locations=merged_freq_region.index,
        color="Number of Volunteers per Region",
        color_continuous_scale="OrRd",
        mapbox_style="carto-positron",
        center={"lat": 50.5, "lon": 4.5},
        zoom=6,
        opacity=0.7,
        labels={"Number of Volunteers per Region": ""})

        fig_volunteers_freq.update_layout(title="Number of Checked In Volunteers per Region")

        # Display table and graphes
        return html.Div([
            dbc.Row([
                dbc.Col(dcc.Dropdown(
                    id='column-selector',
                    options=[{'label': col, 'value': col} for col in columns],
                    multi=True,
                    value=columns,
                    placeholder="Select columns to display",
                    style={'width': '100%'}
                ), width=12)
            ]),
        dcc.Input(
            id='page-size-input',
            type='number',
            value=50,  # Default value
            min=1,
            max=200,
            step=1,
            placeholder='Number of rows per page',
            style={'marginBottom': '10px'}
        ),
        dash_table.DataTable(
            id='attendees-table',
            columns=[{"name": col, "id": col} for col in columns],
            data=df_infos_events_and_attendees.to_dict('records'),
            style_table={'height': '400px', 'overflowY': 'auto'},
            filter_action='native',
            sort_action='native',
            row_selectable='multi',
            page_action='native',
            style_cell={'textAlign': 'left', 'padding': '10px', 'fontSize': '14px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold', 'fontSize': '16px'},
            style_data={'backgroundColor': 'rgb(255, 255, 255)', 'color': 'rgb(50, 50, 50)', 'border': '1px solid rgba(0, 0, 0, 0.1)'}
        ),
            dbc.Row([
                dbc.Col(
                    dbc.Button("Export to CSV", id="export-csv-button", n_clicks=0, color="success", className="mt-3", style={'width': '100%'}),
                    width=6
                ),
                dbc.Col(
                    dbc.Button("Export to XLSX", id="export-xlsx-button", n_clicks=0, color="info", className="mt-3", style={'width': '100%'}),
                    width=6
                )
            ]),
            dcc.Download(id="download-dataframe"),

            dbc.Row([
                dbc.Col(dcc.Graph(figure=age_barplot_participants), width=6),
                dbc.Col(dcc.Graph(figure=gender_barplot_participants), width=6),
                dbc.Col(dcc.Graph(figure=age_barplot_volunteers), width=6),
                dbc.Col(dcc.Graph(figure=gender_barplot_volunteers), width=6),
                dbc.Col(dcc.Graph(figure=fig_dojo_freq), width=6),
                dbc.Col(dcc.Graph(figure=fig_participant_freq), width=6),
                dbc.Col(dcc.Graph(figure=fig_volunteers_freq), width=6)
            ])
        ])
    except RateLimitException as e:
        return html.Div(str(e), style={'color': 'red'})
    except Exception as e:
        return html.Div(f"An error occurred: {str(e)}", style={'color': 'red'})

# Callback to display selected events and attendees
@app.callback(
    Output('event-details', 'children'),
    Input('validate-button', 'n_clicks'),
    State('event-selector', 'value'),
    State('token-store', 'data'),
    State('start-date-picker', 'date'),
    State('end-date-picker', 'date')
)

def display_event_details(n_clicks, selected_event_names, token, start_date, end_date):
    if n_clicks == 0:
        raise PreventUpdate

    if selected_event_names:
        return display_selected_events(selected_event_names, token, start_date, end_date)
    return html.Div("Please select events to display details.")


# Callback to update the table columns
@app.callback(
    Output('attendees-table', 'columns'),
    Input('column-selector', 'value'),
    State('attendees-table', 'data')
)

def update_table_columns(selected_columns, data):
    if not selected_columns:
        raise PreventUpdate
    return [{"name": col, "id": col} for col in selected_columns]


# Callback to update the number of rows per page
@app.callback(
    Output('attendees-table', 'page_size'),
    Input('page-size-input', 'value')
)
def update_page_size(page_size):
    if page_size is None or page_size < 1:
        return 50
    return page_size

# Callback to export table as csv or xlsx
@app.callback(
    Output("download-dataframe", "data"),
    [Input("export-csv-button", "n_clicks"),
     Input("export-xlsx-button", "n_clicks")],
    State("attendees-table", "data"),
    State("column-selector", "value"),
    State("start-date-picker", "date"),
    State("end-date-picker", "date"),
    prevent_initial_call=True
)
def export_table(n_clicks_csv, n_clicks_xlsx, data, selected_columns, start_date, end_date):
    if not data or not selected_columns:
        raise PreventUpdate

    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    df = pd.DataFrame(data)

    df_filtered = df[selected_columns]

    if button_id == "export-csv-button":
        filename = f"custom_report_{start_date}_{end_date}.csv"
        return dcc.send_data_frame(df_filtered.to_csv, filename, index=False, encoding='utf-8-sig')
    elif button_id == "export-xlsx-button":
        filename = f"custom_report_{start_date}_{end_date}.xlsx"
        return dcc.send_data_frame(df_filtered.to_excel, filename, index=False)
    else:
        return html.Div("Error during export. Please try again.", style={'color': 'red'})

if __name__ == '__main__':
    app.run_server(debug=True)