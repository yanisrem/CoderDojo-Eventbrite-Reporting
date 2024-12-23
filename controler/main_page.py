def main_page():
    from dash import dcc, html
    return html.Div([
        html.H2("Custom Report", style={'textAlign': 'center', 'marginBottom': '20px'}),
        html.Div([
            html.Label("Start Date:"),
            dcc.DatePickerSingle(
                id='start-date-picker',
                placeholder='Select a start date',
                style={'marginBottom': '20px'}
            ),
            html.Label("End Date:"),
            dcc.DatePickerSingle(
                id='end-date-picker',
                placeholder='Select an end date',
                style={'marginBottom': '20px'}
            ),
        ], style={'textAlign': 'center', 'marginBottom': '30px'}),
        html.Div([
            html.Button("Filter Events", id="filter-button", n_clicks=0, style={'marginBottom': '20px'}),
            html.Div(id="event-list", style={'marginTop': '20px', 'textAlign': 'center'})
        ], style={'textAlign': 'center'})
    ])