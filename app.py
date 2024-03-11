# Import necessary libraries
import os  
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import pandas as pd
import requests
import json

# Function to fetch publications from ORCID
def fetch_orcid_publications(orcid_id):
    url = f'https://pub.orcid.org/v3.0/{orcid_id}/works'
    headers = {'Accept': 'application/json'}
    response = requests.get(url, headers=headers)
    dois = []
    if response.status_code == 200:
        works = response.json().get('group', [])
        for work in works:
            for external_id in work['work-summary'][0]['external-ids']['external-id']:
                if external_id['external-id-type'] == 'doi':
                    dois.append(external_id['external-id-value'])
    return dois

# Function to fetch metadata from Crossref
def fetch_crossref_metadata(doi):
    url = f'https://api.crossref.org/works/{doi}'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('message', {})
    return {}

# Function to fetch Altmetric data (placeholder implementation)
def fetch_altmetric_data(doi):
    # This is a placeholder implementation. Adjust according to your access to Altmetric data.
    altmetric_url = f'https://api.altmetric.com/v1/doi/{doi}'
    response = requests.get(altmetric_url)
    if response.status_code == 200:
        return response.json()
    return {}

# Function to build publications DataFrame
def build_publications_dataframe(orcid_id):
    dois = fetch_orcid_publications(orcid_id)
    publications_data = []

    for doi in dois:
        metadata = fetch_crossref_metadata(doi)
        altmetric_data = fetch_altmetric_data(doi)  # Placeholder for fetching altmetric data
        

        # Extracting authors
        authors_list = metadata.get('author', [])
        authors_name = [f"{author.get('given')} {author.get('family')}" for author in authors_list  if 'given' in author and 'family' in author]
        authors_list = metadata.get('author', [])
        authors_orcid_url = [{'name': f"{author.get('given')} {author.get('family')}", 'ORCID': author.get('ORCID')} for author in authors_list  if 'given' in author and 'family' in author]
        authors_orcid_id = [{'name': f"{author.get('given')} {author.get('family')}", 'ORCID': author.get('ORCID').replace("http://orcid.org/", "") if author.get('ORCID') else None} for author in authors_list  if 'given' in author and 'family' in author]


        # Extracting simplified metadata for demonstration purposes
        publication_info = {
            'DOI': doi,
            #'URL': metadata.get('URL'),
            'Title': metadata.get('title', []),
            #'Abstract': metadata.get('abstract', []),
            #'Authors_brut': metadata.get('author', []),
            #'Authors Orcid Url': authors_orcid_url,
            #'Authors Orcid Id': authors_orcid_id,
            'Authors Name': authors_name,
           
            #'Authors': ', '.join([author['given'] for author in metadata.get('authors', []) if 'given' in author]),
            #'Created Date': metadata.get('created', {}).get('date-parts', [[None]]),
            'Created Year': metadata.get('created', {}).get('date-parts', [[None]])[0][0],
            #'Published Date': metadata.get('published', {}).get('date-parts', [[None]]),
            'Published Year': metadata.get('published', {}).get('date-parts', [[None]])[0][0],
            'Journal Abbr': metadata.get('short-container-title', []),
            'Journal': metadata.get('container-title', ['']),
            #'Journal Original': metadata.get('original-title', ['']),
            'Language': metadata.get('language', ['']),

            'Volume': metadata.get('volume'),
            'Issue': metadata.get('issue'),
            'Pages': metadata.get('page'),
            #'ISSN': ', '.join(metadata.get('ISSN')),
            'Publisher': metadata.get('publisher'),
            'Publication Type': metadata.get('type'),

            'Subject': metadata.get('subject', ['Unknown']),
            'Funders': metadata.get('funder'),
            'Citation count': metadata.get('is-referenced-by-count'),
            'Source': metadata.get('source'), 

            #'Abstract Altmetric': altmetric_data.get('abstract'),
            #'Authors Altmetric': altmetric_data.get('authors'),
            #'Altmetric is_oa': altmetric_data.get('is_oa'),

            'Altmetric Score': altmetric_data.get('score'),
            'Altmetric Read Count': altmetric_data.get('readers_count'),
            'Altmetric Image': altmetric_data.get('images', {}).get('small') if altmetric_data.get('images') else None,
            'Altmetric URL': altmetric_data.get('details_url')
        }

        publications_data.append(publication_info)
        
    return pd.DataFrame(publications_data)

# Initialize the Dash app
app = dash.Dash(__name__)

# Define the app layout
app.layout = html.Div([
    html.H1("ORCID Publications Fetcher"),
    dcc.Input(id='orcid-input', type='text', placeholder='Enter ORCID ID'),
    html.Button('Submit', id='submit-button', n_clicks=0),
    #html.Button('Download CSV', id='btn_csv'),
    #dcc.Download(id='download-publications-csv'),
    html.Div(id='container-button-basic'),
    
    dcc.Store(id='stored-data'),  # To store the DataFrame temporarily
    html.Button('Download Publications List', id='download-button'),
    dcc.Download(id='download-link')
])

# Define callback to update page
@app.callback(
    Output('container-button-basic', 'children'),
    [Input('submit-button', 'n_clicks')],
    [dash.dependencies.State('orcid-input', 'value')]
)
def update_output(n_clicks, value):
    if n_clicks > 0 and value:
        df = build_publications_dataframe(value)
        if not df.empty:
            # Convert all DataFrame cells to strings, handling lists of dictionaries
            df = df.applymap(lambda x: ', '.join([json.dumps(item) if isinstance(item, dict) else item for item in x]) if isinstance(x, list) else str(x))
            
            # Convert the DataFrame to a simple HTML table for display
            return html.Table(
                # Header
                [html.Tr([html.Th(col) for col in df.columns])] +
                # Body
                [html.Tr([
                    html.Td(df.iloc[i][col]) for col in df.columns
                ]) for i in range(len(df))]
            )
        else:
            return 'No publications found for this ORCID ID.'
    return 'Enter an ORCID ID and click submit.'


# Adjust your callback that generates the DataFrame to store it in dcc.Store
@app.callback(
    Output('stored-data', 'data'),  # Output to the dcc.Store component
    Input('submit-button', 'n_clicks'),  # Triggered by the submit button click
    State('orcid-input', 'value')  # Reads the value from the input without triggering the callback
)
def update_and_store_data(n_clicks, orcid_id):
    if n_clicks is None or orcid_id is None:
        raise dash.exceptions.PreventUpdate
    # Call your function to build the DataFrame based on the ORCID ID
    df = build_publications_dataframe(orcid_id)
    # Convert DataFrame to a dictionary for dcc.Store
    return df.to_dict('records')

# Callback to download the data
@app.callback(
    Output('download-link', 'data'),
    Input('download-button', 'n_clicks'),
    State('stored-data', 'data'),
    prevent_initial_call=True
)
def download_publications_list(n_clicks, stored_data):
    if n_clicks is None or stored_data is None:
        raise PreventUpdate
    # Convert the stored data back to a DataFrame
    df = pd.DataFrame(stored_data)
    # Return the CSV download
    return dcc.send_data_frame(df.to_csv, "publications_list.csv")



# Run the app
if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
