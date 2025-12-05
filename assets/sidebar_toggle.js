
document.addEventListener('DOMContentLoaded', function () {
    // Wait for Dash to load
    setTimeout(function () {
        const toggleBtn = document.getElementById('sidebar-toggle-btn');

        if (toggleBtn) {
            toggleBtn.addEventListener('click', function () {
                document.body.classList.toggle('sidebar-collapsed');

                // Trigger a resize event to update Plotly charts
                setTimeout(function () {
                    window.dispatchEvent(new Event('resize'));
                }, 300);
            });
        }
    }, 2000); // Delay to ensure elements exist
});
