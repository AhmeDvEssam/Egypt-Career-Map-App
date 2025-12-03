from index import app, server

if __name__ == '__main__':
    # new Dash versions use app.run()
    try:
        app.run(debug=True, host='127.0.0.1', port=8050)
    except TypeError:
        # fallback for older versions
        app.run_server(debug=True, host='127.0.0.1', port=8050)
