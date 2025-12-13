window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function (feature, latlng) {
            const props = feature.properties;
            const marker = L.marker(latlng);
            if (props && props.tooltip) {
                marker.bindTooltip(props.tooltip);
            }
            return marker;
        }
    }
});