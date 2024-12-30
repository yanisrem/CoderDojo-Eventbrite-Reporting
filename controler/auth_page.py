def auth_page():
    from dash import dcc, html
    return html.Div([
        html.Div([
            # Ajout de l'image du logo
            html.H1("CoderDojo Eventbrite Reporting", style={'textAlign': 'center', 'marginBottom': '20px'}),
            html.Img(src='/assets/logo-cdj-belgium-transparent.png', style={'display': 'block', 'margin': '0 auto', 'marginBottom': '20px', 'width': '200px'}),
            html.P("Welcome, please insert your personal token", style={'textAlign': 'center', 'marginBottom': '40px'}),
        ], style={'marginBottom': '50px'}),
        html.Div([
            dcc.Input(id='token-input', type='password', placeholder='Enter your token', style={'width': '300px', 'marginBottom': '20px'}),
            html.Button('Submit', id='submit-button', n_clicks=0, style={'display': 'block', 'margin': '0 auto'}),
            html.Div(id='error-message', style={'color': 'red', 'marginTop': '10px', 'textAlign': 'center'})
        ], style={'textAlign': 'center'})
    ], style={'fontFamily': 'Arial, sans-serif', 'padding': '50px'})
