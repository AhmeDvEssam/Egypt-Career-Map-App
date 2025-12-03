// Deep Analysis Click-to-Filter Functionality
// This script enables clicking on chart bars to filter the dashboard

window.addEventListener('DOMContentLoaded', function () {
    console.log('Deep Analysis click-to-filter loaded');

    // Chart IDs that support click-to-filter
    const chartConfigs = {
        'top-companies-chart': 'sidebar-company-filter',
        'education-level-chart': 'sidebar-education-filter',
        'skills-cloud': 'sidebar-career-level-filter',  // Career level chart
        'applicants-chart': 'sidebar-company-filter'
    };

    // Add click listeners to all charts
    Object.keys(chartConfigs).forEach(chartId => {
        const chartElement = document.getElementById(chartId);
        if (chartElement) {
            chartElement.on('plotly_click', function (data) {
                const point = data.points[0];
                const clickedValue = point.y;  // For horizontal bars, the label is on y-axis
                const filterId = chartConfigs[chartId];

                console.log(`Clicked on ${chartId}: ${clickedValue}`);
                console.log(`Target filter: ${filterId}`);

                // Get the filter dropdown element
                const filterElement = document.getElementById(filterId);
                if (filterElement) {
                    // Get current selected values
                    let currentValues = filterElement.value || [];

                    // Toggle the clicked value
                    if (currentValues.includes(clickedValue)) {
                        // Remove if already selected
                        currentValues = currentValues.filter(v => v !== clickedValue);
                    } else {
                        // Add if not selected
                        currentValues = [...currentValues, clickedValue];
                    }

                    // Update the filter
                    filterElement.value = currentValues;

                    // Trigger change event to update the dashboard
                    const event = new Event('change', { bubbles: true });
                    filterElement.dispatchEvent(event);

                    console.log(`Updated ${filterId} with values:`, currentValues);
                } else {
                    console.warn(`Filter element not found: ${filterId}`);
                }
            });
        }
    });
});
