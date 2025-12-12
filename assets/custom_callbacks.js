window.dash_clientside = Object.assign({}, window.dash_clientside, {
    clientside: {
        close_popup: function (n_clicks) {
            if (n_clicks) {
                return { 'display': 'none' };
            }
            return window.dash_clientside.no_update;
        }
    }
});

window.bindTooltip = function (feature, layer) {
    if (feature.properties && feature.properties.tooltip) {
        layer.bindTooltip(feature.properties.tooltip);
    }
    // Bind Click to Open URL
    if (feature.properties && feature.properties.link) {
        layer.on('click', function () {
            window.open(feature.properties.link, '_blank');
        });
    }
};
