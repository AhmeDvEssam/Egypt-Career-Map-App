window.dash_clientside = Object.assign({}, window.dash_clientside, {
    clientside: {
        update_map_class: function (zoom_data) {
            if (!zoom_data) {
                return 'map-low-zoom';
            }
            // data is {zoom: X, center: {...}}
            // Threshold for showing labels: Zoom > 7
            if (zoom_data.zoom > 7) {
                return 'map-high-zoom';
            }
            return 'map-low-zoom';
        },

        apply_theme: function (theme_data) {
            // Existing theme logic...
            if (theme_data === 'dark') {
                document.body.classList.add('dark-theme');
                document.body.classList.remove('light-theme');
                return 'dark';
            } else {
                document.body.classList.add('light-theme');
                document.body.classList.remove('dark-theme');
                return 'light';
            }
        }
    }
});
