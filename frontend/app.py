import os
import dash
from dash import Dash, html, dcc, Output, Input, State
import dash_bootstrap_components as dbc
from frontend.auth import register_auth_callbacks
from frontend.callbacks.routing_callbacks import register_routing_callbacks
from frontend.callbacks.data_callbacks import register_data_callbacks
from frontend.callbacks.admin_callbacks import register_admin_callbacks

app = Dash(
    __name__,
    use_pages=True,
    pages_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pages'),
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css",
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
    ],
    external_scripts=[
        "https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js",
        "https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"
    ],
    suppress_callback_exceptions=True
)
app.title = "UIDAI analytics Dashboard"

content = html.Div(
    dash.page_container,
    id="main-content",
    className="main-content"
)

app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        dcc.Store(id="auth-state", storage_type="session"),
        dcc.Store(id="company-list-version", data=0),
        dcc.Store(id="data-store", storage_type="memory"),
        dcc.Download(id="download-dataframe-csv"),
        html.Div(id="app-container")
    ]
)

# Clientside callbacks for websockets
app.clientside_callback(
    """
    function(token) {
        if (!token) return window.dash_clientside.no_update;
        
        let clientId = window.sessionStorage.getItem('ws_client_id');
        if (!clientId) {
            clientId = 'client-' + Math.random().toString(36).substring(2, 15);
            window.sessionStorage.setItem('ws_client_id', clientId);
        }
        
        if (window.app_ws) {
            window.app_ws.close();
        }
        
        // Ensure WebSocket URL matches the host
        const wsUrl = (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + 'localhost:8000/ws/progress/' + clientId;
        const ws = new WebSocket(wsUrl);
        window.app_ws = ws;
        
        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            console.log("WS Data:", data);
            
            // Update progress bar
            const progBar = document.querySelector('#upload-progress .progress-bar');
            if (progBar && data.progress !== undefined) {
                progBar.style.width = data.progress + '%';
                progBar.setAttribute('aria-valuenow', data.progress);
                progBar.textContent = data.progress + '%';
            }
            
            // Update status text
            const statusDiv = document.getElementById('upload-status');
            if (statusDiv && data.message) {
                statusDiv.innerText = data.message;
            }
            
            // Trigger Python callback if complete
            if (data.status === 'complete') {
                const wsDataInput = document.getElementById('ws-data');
                if (wsDataInput) {
                    wsDataInput.value = event.data;
                    wsDataInput.dispatchEvent(new Event('input', { bubbles: true }));
                    
                    setTimeout(() => {
                        const trigger = document.getElementById('ws-trigger');
                        if (trigger) trigger.click();
                    }, 100);
                }
            }
        };
        
        return clientId;
    }
    """,
    Output('ws-client-id', 'data'),
    Input('auth-state', 'data'),
    prevent_initial_call=False
)

register_auth_callbacks(app)
register_routing_callbacks(app, content)
register_data_callbacks(app)
register_admin_callbacks(app)

if __name__ == '__main__':
    app.run(debug=True, port=8050)
