import dash
import dash_bootstrap_components as dbc
from flask_caching import Cache

# Create Dash app instance
# Custom CSS will be automatically loaded from assets/custom.css
app = dash.Dash(
    __name__, 
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css'
    ], 
    suppress_callback_exceptions=True,
    meta_tags=[
        # Mobile viewport configuration
        {"name": "viewport", "content": "width=device-width, initial-scale=1, maximum-scale=5, user-scalable=yes"},
        # PWA support
        {"name": "mobile-web-app-capable", "content": "yes"},
        {"name": "apple-mobile-web-app-capable", "content": "yes"},
        {"name": "apple-mobile-web-app-status-bar-style", "content": "black-translucent"},
    ]
)
server = app.server

# Initialize cache for map performance
cache = Cache(app.server, config={
    'CACHE_TYPE': 'simple',  # In-memory cache
    'CACHE_DEFAULT_TIMEOUT': 300  # 5 minutes
})

