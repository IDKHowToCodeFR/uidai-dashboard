import dash
from frontend.auth import login_page

dash.register_page(__name__, path='/login', name='Login')

layout = login_page
