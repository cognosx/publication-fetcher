
import dash_bootstrap_components as dbc
from dash import dcc, html


# def Navbar():
#     navbar = dbc.NavbarSimple(
#         children=[
#             dbc.NavItem(dcc.Link('Home', href='/', className='nav-link')),
#             dbc.NavItem(dcc.Link('Inventors', href='/inventor', className='nav-link')),
#             dbc.NavItem(dcc.Link('Applicants', href='/applicants', className='nav-link')),
#             dbc.NavItem(dcc.Link('Applicant countries', href='/applicants_countries', className='nav-link')),
#             dbc.NavItem(dcc.Link('Jurisdictions', href='/jurisdiction', className='nav-link')),
#         ],
#         brand="Immune Checkpoint Therapy Patent Analysis",
#         brand_href="/",
#         color="primary",
#         dark=True,
#         className="mb-4"
#     )
#     return navbar

def Footer():
    footer = html.Footer(
        dbc.Container(
            dbc.Row(
                dbc.Col(
                    html.Small("Last Updated: 17/03/2024 | By CognosX"), #Data Source: Lens.org | 
                    className="text-center"
                )
            )
        ),
        className="footer mt-auto py-3 bg-light"
    )
    return footer

# Example Navbar definition
def Navbar():
    return dbc.Navbar(
        dbc.Container([
            dbc.Col(html.Img(src='/assets/cognosx_logo.png', height="60px")),
            #dbc.NavbarBrand("Methods", href="#"),
            dbc.NavbarBrand("Contacts", href="#"),
            # Add more navbar items here
        ]),
        color="dark",
        dark=True,
    )


# dbc.Row(
#     dbc.Col(
#         html.P(
#             [
#                 "Powered by ",
#                 html.A("CognosX", href="https://www.cognosx.com", target="_blank"),
#             ],
#             className="text-center"
#         ),
#     ),
#     className="mt-auto py-3 bg-light",
# ),

