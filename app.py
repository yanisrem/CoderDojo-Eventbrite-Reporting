import dash
from dash import dcc, html, Input, Output, State, dash_table
from dash.exceptions import PreventUpdate
import requests
import pandas as pd
from controler.auth_page import auth_page
from controler.main_page import main_page
from api.request_eventbrite import get_filter_events_organization, get_event_attendees, RateLimitException
from services.events import extract_event_informations, extract_attendee_informations, extract_list_name_events
from concurrent.futures import ThreadPoolExecutor
import dash_bootstrap_components as dbc
import plotly.express as px
from dash.long_callback import DiskcacheLongCallbackManager

## Diskcache
import diskcache
cache = diskcache.Cache("./cache")
long_callback_manager = DiskcacheLongCallbackManager(cache)

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
@app.long_callback(
    Output('event-list', 'children'),
    Input('filter-button', 'n_clicks'),
    State('start-date-picker', 'date'),
    State('end-date-picker', 'date'),
    State('token-store', 'data'),  # Get stored token
    manager=long_callback_manager,
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

        columns = df_infos_events_and_attendees.columns.tolist()

        # Age barplot
        age_category_counts = df_infos_events_and_attendees['Age'].value_counts(normalize=True).reset_index()
        age_category_counts.columns = ['Age', 'Frequency']
        age_category_counts['Frequency'] = age_category_counts['Frequency'] * 100
        age_category_counts = age_category_counts.nlargest(15, 'Frequency')
        age_barplot = px.bar(
            age_category_counts,
            x='Age', y='Frequency',
            title="Age distribution of attendees",
            labels={'Age': 'Age', 'Frequency': 'Frequency (in %)'},
            color='Age',
            color_continuous_scale='Viridis'
        )
        age_barplot.update_layout(showlegend=False)

        # Gender barplot
        gender_category_counts = df_infos_events_and_attendees['Gender'].value_counts(normalize=True).reset_index()
        gender_category_counts.columns = ["Gender", "Frequency"]
        gender_category_counts['Frequency'] = gender_category_counts['Frequency'] * 100
        gender_barplot = px.bar(
            gender_category_counts,
            x='Gender', y='Frequency',
            title="Attendees by gender",
            labels={'Gender': 'Gender', 'Frequency': 'Frequency (in %)'},
            color='Gender',
            color_discrete_map={'male': 'blue', 'female': 'pink'}
        )

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
            dash_table.DataTable(
                id='attendees-table',
                columns=[{"name": col, "id": col} for col in columns],
                data=df_infos_events_and_attendees.to_dict('records'),
                style_table={'height': '400px', 'overflowY': 'auto'},
                filter_action='native',
                sort_action='native',
                row_selectable='multi',
                page_size=10,
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
                dbc.Col(dcc.Graph(figure=age_barplot), width=6),
                dbc.Col(dcc.Graph(figure=gender_barplot), width=6)
            ])
        ])
    except RateLimitException as e:
        return html.Div(str(e), style={'color': 'red'})
    except Exception as e:
        return html.Div(f"An error occurred: {str(e)}", style={'color': 'red'})


# Callback to display selected events and attendees
@app.long_callback(
    Output('event-details', 'children'),
    Input('validate-button', 'n_clicks'),
    State('event-selector', 'value'),
    State('token-store', 'data'),
    State('start-date-picker', 'date'),
    State('end-date-picker', 'date'),
    manager=long_callback_manager
)
def display_event_details(n_clicks, selected_event_names, token, start_date, end_date):
    if n_clicks == 0:
        raise PreventUpdate

    if selected_event_names:
        return display_selected_events(selected_event_names, token, start_date, end_date)
    return html.Div("Please select events to display details.")


# Callback to update the table
@app.long_callback(
    Output('attendees-table', 'columns'),
    Input('column-selector', 'value'),
    State('attendees-table', 'data'),
    manager=long_callback_manager
)
def update_table_columns(selected_columns, data):
    if not selected_columns:
        raise PreventUpdate
    return [{"name": col, "id": col} for col in selected_columns]


# Callback to export table as csv or xlsx
@app.long_callback(
    Output("download-dataframe", "data"),
    [Input("export-csv-button", "n_clicks"),
     Input("export-xlsx-button", "n_clicks")],
    State("attendees-table", "data"),
    State("column-selector", "value"),
    State("start-date-picker", "date"),
    State("end-date-picker", "date"),
    prevent_initial_call=True,
    manager=long_callback_manager
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