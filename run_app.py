import sys
import os
import webbrowser
from threading import Timer
from index import app

# Function to open browser
def open_browser():
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        webbrowser.open_new("http://127.0.0.1:8050")

if __name__ == '__main__':
    # Adjust paths for PyInstaller if needed (though data_loader handles it now)
    if getattr(sys, 'frozen', False):
        # If specific assets configs needed, set here
        pass

    Timer(1, open_browser).start()
    
    # Run server
    # debug=False is important for production/EXE
    app.run_server(debug=False, port=8050)
