# Standard library imports
import re
import requests

# Third-party imports
import dash
import pandas as pd
from dash import dcc, html, dash_table, Input, Output, State
from dash.exceptions import PreventUpdate
from flask_caching import Cache
import dash_bootstrap_components as dbc

# Initialize the Dash app with Bootstrap and server-side caching
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
cache = Cache(app.server, config={'CACHE_TYPE': 'filesystem', 'CACHE_DIR': 'cache-directory'})

# Layout definition
app.layout = dbc.Container([
    dbc.Row(dbc.Col(html.H1('ORCID Publications Fetcher'))),
    dbc.Row(dbc.Col(html.P("Enter your ORCID ID to fetch and display your publications."))),
    dbc.Row(dbc.Col(dcc.Input(id='orcid-input', type='text', placeholder='e.g., 0000-0002-1825-0097', debounce=True, className="mb-3"))),
    dbc.Row(dbc.Col(html.Button('Submit', id='submit-button', n_clicks=0, className="mb-3"))),
    dbc.Row(dbc.Col(dbc.Spinner(id='loading-spinner', children=[], size="lg", color="primary", type="border", fullscreen=False))),
    dbc.Row(dbc.Col(html.Button('Download Publications List', id='download-button', disabled=True))),
    dcc.Download(id='download-link'),
    dcc.Store(id='stored-data'),
    html.Div(id='table-container')  # Placeholder for potential additional content
], fluid=True)

# Data fetching and processing functions
@cache.memoize()
def fetch_orcid_publications(orcid_id):
    """Fetches publication DOIs from ORCID."""
    url = f'https://pub.orcid.org/v3.0/{orcid_id}/works'
    headers = {'Accept': 'application/json'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        works = response.json().get('group', [])
        dois = [
            external_id['external-id-value']
            for work in works
            for external_id in work['work-summary'][0]['external-ids']['external-id']
            if external_id['external-id-type'] == 'doi'
        ]
        return dois, None
    except requests.RequestException as e:
        print(f"Error fetching ORCID publications: {e}")
        return [], str(e)

@cache.memoize()
def fetch_metadata(doi):
    """Fetches metadata from CrossRef and Altmetric by DOI."""
    crossref_url = f'https://api.crossref.org/works/{doi}'
    altmetric_url = f'https://api.altmetric.com/v1/doi/{doi}'
    metadata, altmetric_data = {}, {}
    
    try:
        crossref_response = requests.get(crossref_url)
        crossref_response.raise_for_status()
        metadata = crossref_response.json().get('message', {})
    except requests.RequestException as e:
        print(f"Error fetching Crossref metadata: {e}")
    
    try:
        altmetric_response = requests.get(altmetric_url)
        altmetric_response.raise_for_status()
        altmetric_data = altmetric_response.json()
    except requests.RequestException as e:
        print(f"Error fetching Altmetric data: {e}")
    
    return compile_publication_info(doi, metadata, altmetric_data)

def compile_publication_info(doi, metadata, altmetric_data):
    """Compiles publication information from metadata and altmetric data."""
    authors_list = metadata.get('author', [])
    authors_name = [f"{author.get('given')} {author.get('family')}" for author in authors_list if 'given' in author and 'family' in author]
    return {
        'DOI': doi,
        'Title': metadata.get('title', [''])[0],
        'Authors Name': ', '.join(authors_name),
        # Additional fields as per original function...
    }

# Callbacks for interactivity
@app.callback(
    Output('submit-button', 'disabled'),
    Input('orcid-input', 'value')
)
def validate_orcid_input(value):
    """Validates the ORCID ID format."""
    if value is None or not isinstance(value, str):
        return True  # Disable the button if the input is not a string
    is_valid = re.match(r'^\d{4}-\d{4}-\d{4}-\d{4}$', value) is not None
    return not is_valid




@app.callback(
    Output('loading-spinner', 'children'),
    Input('submit-button', 'n_clicks'),
    State('orcid-input', 'value'),
    prevent_initial_call=True
)
def update_table(n_clicks, orcid_id):
    """Updates the table with publications data."""
    if not orcid_id:
        return dbc.Alert("Please enter a valid ORCID ID.", color="warning")

    dois, error = fetch_orcid_publications(orcid_id)
    if error:
        return dbc.Alert(f"Error fetching publications: {error}", color="danger")
    
    if not dois:
        return dbc.Alert("No publications found for the provided ORCID ID.", color="warning")
    
    publications_data = [fetch_metadata(doi) for doi in dois]
    df = pd.DataFrame(publications_data)
    
    # Table and download button update...
    # Code for displaying the table and enabling download button goes here...

# Additional callbacks for download functionality, tooltips, etc.
def update_table_and_controls(n_clicks, orcid_id):
    """Updates the table with publication data and controls the download button."""
    if not orcid_id:
        return dbc.Alert("Please enter a valid ORCID ID.", color="warning")

    dois, error = fetch_orcid_publications(orcid_id)
    if error:
        return dbc.Alert(f"Error fetching publications: {error}", color="danger")

    publications_data = [fetch_metadata(doi) for doi in dois]
    df = pd.DataFrame(publications_data)

    if df.empty:
        return dbc.Alert("No publications found for the provided ORCID ID.", color="warning")

    table = dash_table.DataTable(
        id='publications-table',
        columns=[{"name": i, "id": i} for i in df.columns],
        data=df.to_dict('records'),
        filter_action='native',
        sort_action='native',
        sort_mode='multi',
        page_size=10,
        style_cell={'overflow': 'hidden', 'textOverflow': 'ellipsis', 'maxWidth': 200},
        tooltip_delay=0,
        tooltip_duration=None
    )

    download_button_enabled = not df.empty
    return dbc.Spinner([table, html.Button('Download Publications List', id='download-button', disabled=not download_button_enabled, className="mb-3")], size="lg", color="primary", type="border", fullscreen=True)

@app.callback(
    Output('download-link', 'data'),
    Input('download-button', 'n_clicks'),
    State('orcid-input', 'value'),
    prevent_initial_call=True
)
def generate_download(n_clicks, orcid_id):
    """Generates a CSV file for download."""
    if n_clicks is None or orcid_id is None:
        raise PreventUpdate

    dois, _ = fetch_orcid_publications(orcid_id)
    publications_data = [fetch_metadata(doi) for doi in dois]
    df = pd.DataFrame(publications_data)

    return dcc.send_data_frame(df.to_csv, "publications.csv")

# @app.callback(
#     Output('orcid-input', 'text'),
#     Input('orcid-input', 'value')
# )
# def update_input_tooltip(value):
#     """Updates tooltip for ORCID input based on user interaction."""
#     if not value:
#         return "Enter your ORCID ID here. It should look like 0000-0000-0000-0000."
#     return "Your ORCID ID is being validated. Please ensure it is in the correct format."

# Remember to import necessary modules and adjust any logic to fit your actual application needs

if __name__ == '__main__':
    app.run_server(debug=True)
