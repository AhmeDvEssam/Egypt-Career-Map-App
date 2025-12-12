window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function (feature, latlng, context) {
            const { tooltip, popup } = feature.properties;
            const marker = L.marker(latlng);
            if (tooltip) marker.bindTooltip(tooltip);
            if (popup) marker.bindPopup(popup);
            return marker;
        },
    },
    renderMarker: function (feature, latlng) {
        console.log("DEBUG: renderMarker called", feature);
        const props = feature.properties;
        const marker = L.marker(latlng);

        // ... (Template Logic) ...

        let city_str = props.city || "";
        if (props.in_city && props.in_city.toLowerCase() !== 'nan' && props.in_city !== 'None') {
            city_str += " | " + props.in_city;
        }

        const html = `
            <div style="font-family: 'Segoe UI', sans-serif; min-width: 180px;">
                <div style="font-weight: bold; font-size: 14px; color: #d32f2f; margin-bottom: 3px;">${props.title}</div>
                <div style="font-size: 13px; font-weight: 600; color: #333; margin-bottom: 3px;">${props.company}</div>
                <div style="font-size: 12px; color: #666; margin-bottom: 6px;">${city_str}</div>
                <div style="font-size: 11px; color: #0066CC; font-weight: bold;">Click to Visit Job Link ➜</div>
            </div>`;

        marker.bindTooltip(html);
        return marker;
    },
    bindTooltipJS: function (feature, layer) {
        console.log("DEBUG: bindTooltipJS called", feature);
        const props = feature.properties;

        let city_str = props.city || "";
        if (props.in_city && props.in_city.toLowerCase() !== 'nan' && props.in_city !== 'None') {
            city_str += " | " + props.in_city;
        }

        const html = `
            <div style="font-family: 'Segoe UI', sans-serif; min-width: 180px;">
                <div style="font-weight: bold; font-size: 14px; color: #d32f2f; margin-bottom: 3px;">${props.title}</div>
                <div style="font-size: 13px; font-weight: 600; color: #333; margin-bottom: 3px;">${props.company}</div>
                <div style="font-size: 12px; color: #666; margin-bottom: 6px;">${city_str}</div>
                <div style="font-size: 11px; color: #0066CC; font-weight: bold;">Click to Visit Job Link ➜</div>
            </div>`;

        layer.bindTooltip(html);
    }
}
});