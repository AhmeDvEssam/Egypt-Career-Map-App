// ============================================
// CLICK-TO-FILTER CLIENTSIDE CALLBACKS
// ============================================

window.dash_clientside = Object.assign({}, window.dash_clientside, {
    clientside: {
        // Handle Employment Type chart clicks
        filter_by_employment_type: function (clickData) {
            if (!clickData || !clickData.points || clickData.points.length === 0) {
                return window.dash_clientside.no_update;
            }
            const value = clickData.points[0].y;
            return [value];
        },

        // Handle Work Mode chart clicks (pie chart)
        filter_by_work_mode: function (clickData) {
            if (!clickData || !clickData.points || clickData.points.length === 0) {
                return window.dash_clientside.no_update;
            }
            const value = clickData.points[0].label;
            return [value];
        },

        // Handle Career Level chart clicks
        filter_by_career_level: function (clickData) {
            if (!clickData || !clickData.points || clickData.points.length === 0) {
                return window.dash_clientside.no_update;
            }
            const value = clickData.points[0].y;
            return [value];
        },

        // Handle Top Categories chart clicks
        filter_by_category: function (clickData) {
            if (!clickData || !clickData.points || clickData.points.length === 0) {
                return window.dash_clientside.no_update;
            }
            const value = clickData.points[0].y;
            return [value];
        },

        // Handle City chart clicks
        filter_by_city: function (clickData) {
            if (!clickData || !clickData.points || clickData.points.length === 0) {
                return window.dash_clientside.no_update;
            }
            const value = clickData.points[0].y;
            return [value];
        },

        // Handle Top Companies chart clicks
        filter_by_company: function (clickData) {
            if (!clickData || !clickData.points || clickData.points.length === 0) {
                return window.dash_clientside.no_update;
            }
            const value = clickData.points[0].y;
            return [value];
        },

        // Handle Education Level chart clicks (pie chart)
        filter_by_education: function (clickData) {
            if (!clickData || !clickData.points || clickData.points.length === 0) {
                return window.dash_clientside.no_update;
            }
            const value = clickData.points[0].label;
            return [value];
        }
    }
});
