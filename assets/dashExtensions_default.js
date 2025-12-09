window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(feature, latlng, context) {
            const {
                tooltip,
                popup
            } = feature.properties;
            const marker = L.marker(latlng);
            if (tooltip) marker.bindTooltip(tooltip);
            if (popup) marker.bindPopup(popup);
            return marker;
        }
    }
});