# Import required libraries
from components import Navbar, Footer
import os 
import dash
import pandas as pd
import requests
from dash import dcc, html, dash_table, callback_context, Input, Output, State, no_update, callback
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import re
from flask_caching import Cache
import time


# Initialize the Dash app with Bootstrap and server-side caching
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
cache = Cache(app.server, config={'CACHE_TYPE': 'filesystem', 'CACHE_DIR': 'cache-directory'})

# Define the layout of the app
app.layout = dbc.Container([
    # Header with logo
    Navbar(),  # Use the Navbar code snippet from above

    dbc.Row(dbc.Col(html.H1('Publications Fetcher'), 
        width={"size": 6, "offset": 3}, 
        className="d-flex justify-content-center")),
    dbc.Row(dbc.Col(html.P("Enter your ORCID ID to fetch and display your publications."), 
        className="d-flex justify-content-center")),
    dbc.Row(
        dbc.Col([
            dcc.Input(id='orcid-input', type='text', placeholder='e.g., 0000-0002-1825-0097', debounce=True, className="me-2"),
            html.Button('Submit', id='submit-button', n_clicks=0, style={'backgroundColor': '#ffa500', 'color': 'white', 'border': 'none'})
        ], width=12, className="d-flex justify-content-center"),
        justify="center"  # This centers the row
    ),
    dbc.Row(dbc.Col(dbc.Alert(id='input-alert', 
        color="warning", 
        className="mt-3", 
        style={"display": "none"}))),
    dbc.Row(dbc.Col(dbc.Alert(id='status-alert', 
        children="The ORCID number is valid. Fetching publications, please wait...", 
        # is_open=True, 
        # disabled=True, 
        color="info", 
        className="mt-3", 
        style={"display": "none"}))),
    dbc.Row(dbc.Col(dbc.Alert(id='status-alert-output', 
        children="Publications ready. You can now view or download the list.", 
        # is_open=True, 
        # disabled=True, 
        color="info", 
        className="mt-3", 
        style={"display": "none"}))),

    dbc.Row(dbc.Col(html.Div(id='spinner-container', 
        children=[dbc.Spinner(size="lg", 
        color="primary", type="border")], 
        style={'display': 'none'}))),
    dbc.Row(dbc.Col(html.Div(id='spinner-container-closed', 
        children=[dbc.Spinner(size="lg", 
        color="primary", type="border")], 
        style={'display': 'none'}))),

    dbc.Row(dbc.Col(html.Button('Download Publications List', 
        id='download-button', 
        disabled=True, 
        className="mt-3",
        style={'display': 'none'}))),
    dcc.Download(id='download-link'),

    dcc.Store(id='stored-data'),
    dcc.Store(id='stored-orcid-id'),  # Add this

    html.Div(id='table-container', className="mt-3"),  # Placeholder for table
    # Footer
    Footer(),  # Use the Footer code snippet from above

], fluid=True, className="py-3")



#############functions to fetch############################

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
        #'Altmetric Image': altmetric_data.get('images', {}).get('small'),
        #'Altmetric URL': altmetric_data.get('details_url')
    }




####################################################""abs


@app.callback(
    [
        Output('status-alert', 'children'),  # To update the message
        Output('status-alert', 'style'),  # To show/hide the message alert
        Output('spinner-container', 'style'),  # To show/hide the spinner
        Output('stored-orcid-id', 'data'),  # To store the ORCID ID if valid
        Output('table-container', 'children'),  # To display the data table
        Output('download-button', 'disabled'),  # To enable/disable the download button
        Output('download-button', 'style'),  # To show/hide the download button
        Output('stored-data', 'data'),  # To store the fetched data for download
    ],
    [Input('submit-button', 'n_clicks')],
    [State('orcid-input', 'value')],
    prevent_initial_call=True
)
def validate_fetch_and_update_ui(n_clicks, orcid_id):
    if not orcid_id or not re.match(r'^\d{4}-\d{4}-\d{4}-[\dX]{4}$', orcid_id):
        return (
            "Missing or Invalid ORCID ID format. Please correct it and try again.",
            {'display': 'block', 'color': 'warning'},
            {'display': 'none'},  # Hide spinner
            no_update,
            no_update,
            True,
            {'display': 'none'},
            no_update,
        )

    # Valid ORCID ID, start fetching data
    # Show spinner and update message
    spinner_style = {'display': 'block'}  # Make spinner visible
    message = "The ORCID number is valid. Fetching publications, please wait..."
    alert_style = {'display': 'block', 'color': 'primary'}

    try:
        df = build_publications_dataframe(orcid_id)
        if df.empty:
            # Handle empty DataFrame (no publications found)
            return (
                "No publications found for the provided ORCID ID.",
                {'display': 'block', 'color': 'secondary'},
                {'display': 'none'},  # Hide spinner
                orcid_id,
                no_update,
                True,
                {'display': 'none'},
                no_update,
            )

        # Publications fetched, prepare the data table
        # table = prepare_data_table(df)  # Assume this is a function that prepares the Dash DataTable
        tooltip_data = [
            {column: {'value': str(value), 'type': 'markdown'} for column, value in row.items()}
            for row in df.to_dict('records')
        ]
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


        return (
            "Publications ready. You can now view or download the list.",
            {'display': 'block', 'color': 'success'},
            {'display': 'none'},  # Hide spinner after fetching
            orcid_id,
            table,
            False,  # Enable download button
            {'display': 'block'},  # Show download button
            df.to_dict('records'),
        )
    except Exception as e:
        # Handle any exceptions during the fetching process
        return (
            f"An error occurred: {str(e)}",
            {'display': 'block', 'color': 'danger'},
            {'display': 'none'},  # Hide spinner
            no_update,
            no_update,
            True,
            {'display': 'none'},
            no_update,
        )




#####################################################################################################
# Additional callback for download functionality would go here
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
    # Return the CSV download, dynamically naming the file with the ORCID ID
    return dcc.send_data_frame(df.to_csv, filename, index=False)



if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
