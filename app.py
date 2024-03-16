import os 
import dash
import pandas as pd
import requests
from dash import dcc, html, dash_table, callback_context
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from flask_caching import Cache
import dash_bootstrap_components as dbc
import re
from dash import no_update  # Import no_update for cases where no update is required 

# Initialize the Dash app with Bootstrap and server-side caching
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
cache = Cache(app.server, config={'CACHE_TYPE': 'filesystem', 'CACHE_DIR': 'cache-directory'})

app.layout = dbc.Container([
    dbc.Row(dbc.Col(html.H1('ORCID Publications Fetcher'))),
    dbc.Row(dbc.Col(html.P("Enter your ORCID ID to fetch and display your publications."))),
    dbc.Row(dbc.Col(dcc.Input(
        id='orcid-input', type='text', placeholder='e.g., 0000-0002-1825-0097', 
        debounce=True, className="mb-3"
    ))),
    dbc.Row(dbc.Col(html.Button('Submit', id='submit-button', n_clicks=0, className="mb-3"))),
    dbc.Row(dbc.Col(html.Div(id='spinner-container', children=[dbc.Spinner(size="lg", color="primary", type="border")], style={'display': 'none'}))),
    # dbc.Row(dbc.Col(dbc.Spinner(id='loading-spinner', children=[], size="lg", color="primary", type="border", fullscreen=False, style={'display': 'none'}))),
    dbc.Row(dbc.Col(html.Button('Download Publications List', id='download-button', disabled=True))),
    dcc.Download(id='download-link'),
    dcc.Store(id='stored-data'),
    html.Div(id='table-container')  # Placeholder for potential additional content
], fluid=True)


@cache.memoize()
def fetch_orcid_publications(orcid_id):
    url = f'https://pub.orcid.org/v3.0/{orcid_id}/works'
    headers = {'Accept': 'application/json'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raises HTTPError for bad responses
        works = response.json().get('group', [])
        dois = [
            external_id['external-id-value']
            for work in works
            for external_id in work['work-summary'][0]['external-ids']['external-id']
            if external_id['external-id-type'] == 'doi'
        ]
        return dois
    except requests.RequestException as e:
        print(f"Error fetching ORCID publications: {e}")
        return []

@cache.memoize()
def fetch_crossref_metadata(doi):
    url = f'https://api.crossref.org/works/{doi}'
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json().get('message', {})
    except requests.RequestException as e:
        print(f"Error fetching Crossref metadata: {e}")
        return {}

@cache.memoize()
def fetch_altmetric_data(doi):
    altmetric_url = f'https://api.altmetric.com/v1/doi/{doi}'
    try:
        response = requests.get(altmetric_url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching Altmetric data: {e}")
        return {}

def build_publications_dataframe(orcid_id):
    dois = fetch_orcid_publications(orcid_id)
    publications_data = [collect_publication_info(doi) for doi in dois]
    return pd.DataFrame(publications_data)

def collect_publication_info(doi):
    metadata = fetch_crossref_metadata(doi)
    altmetric_data = fetch_altmetric_data(doi)
    authors_list = metadata.get('author', [])
    authors_name = [f"{author.get('given')} {author.get('family')}" for author in authors_list if 'given' in author and 'family' in author]
    return {
        'DOI': doi,
        'Title': metadata.get('title', [''])[0],
        'Authors Name': ', '.join(authors_name),
        'Published Year': metadata.get('published', {}).get('date-parts', [[None]])[0][0],
        'Journal': ', '.join(metadata.get('container-title', [])),
        'Publisher': metadata.get('publisher', ''),
        'Publication Type': metadata.get('type', ''),
        'Subject': ', '.join(metadata.get('subject', [])),
        'Funders': ', '.join(funder.get('name', '') for funder in metadata.get('funder', [])),
        'Citation count': metadata.get('is-referenced-by-count', 0),
        'Altmetric Score': altmetric_data.get('score'),
        'Altmetric Read Count': altmetric_data.get('readers_count'),
        'Altmetric Image': altmetric_data.get('images', {}).get('small'),
        'Altmetric URL': altmetric_data.get('details_url')
    }


@app.callback(
    [
        Output('table-container', 'children'),
        Output('submit-button', 'disabled'),  # Disable the submit button to indicate processing
        Output('spinner-container', 'style'),
        Output('stored-data', 'data'),
        Output('download-button', 'disabled')
    ],
    [Input('submit-button', 'n_clicks')],
    [State('orcid-input', 'value')],
    prevent_initial_call=True
)
def update_table(n_clicks, orcid_id):
    if not orcid_id:
        return dbc.Alert("Please enter a valid ORCID ID.", color="warning"), False, {'display': 'none'}, no_update, True

    if not re.match(r'^\d{4}-\d{4}-\d{4}-[\dX]{4}$', orcid_id):
        return dbc.Alert("Please enter a valid ORCID ID format (e.g., 0000-0002-1825-0097).", color="warning"), False, {'display': 'none'}, no_update, True
    
    # ORCID ID is valid, show the spinner while fetching data
    spinner_style = {'display': 'block'}  # Make the spinner visible
 
    df = build_publications_dataframe(orcid_id)
    if df.empty:
        return dbc.Alert("No publications found for the provided ORCID ID.", color="warning"), False, {'display': 'none'}, no_update, True


    # Generate tooltip data for each cell
    tooltip_data = [
        {column: {'value': str(value), 'type': 'markdown'} for column, value in row.items()}
        for row in df.to_dict('records')
    ]

    # spinner_style = {'display': 'block'}  # Make the spinner visible
    # Create the table with tooltips
    table = dbc.Spinner(dash_table.DataTable(
        id='table-filtering',
        columns=[{"name": i, "id": i} for i in df.columns],
        data=df.to_dict('records'),
        filter_action='native',
        sort_action='native',
        sort_mode='multi',
        page_size=10,
        style_cell={'overflow': 'hidden', 'textOverflow': 'ellipsis', 'maxWidth': 200},
        tooltip_data=tooltip_data,
        tooltip_delay=0,
        tooltip_duration=None
    ), size="lg", color="primary", type="border", fullscreen=True)

    # Once data fetching and processing are complete, hide the spinner again
    spinner_style = {'display': 'none'}  # Hide spinner

    # Enable the submit button again after processing
    return table, False, spinner_style, df.to_dict('records'), False



# Additional callback for download functionality would go here
# Example: Download button callback to generate a CSV of the table data
# Callback to download the data
@app.callback(
    Output('download-link', 'data'),
    [Input('download-button', 'n_clicks')],
    [State('stored-data', 'data'),  # Keeps existing state for the data
     State('orcid-input', 'value')],  # Adds the ORCID ID as a state
    prevent_initial_call=True
)
def download_publications_list(n_clicks, stored_data, orcid_id):
    if n_clicks is None or stored_data is None:
        raise PreventUpdate
    # Sanitize the ORCID ID to ensure it's safe for use in a filename
    # This removes any characters that might be invalid for filenames
    safe_orcid_id = re.sub(r'[^\w\-_]', '_', orcid_id)
    filename = f"{safe_orcid_id}_publications_list.csv"
    # Convert the stored data back to a DataFrame
    df = pd.DataFrame(stored_data)
    # Once data fetching and processing are complete, hide the spinner again
    # spinner_style = {'display': 'none'}  # Hide spinner
    # Return the CSV download, dynamically naming the file with the ORCID ID
    return dcc.send_data_frame(df.to_csv, filename, index=False)

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
