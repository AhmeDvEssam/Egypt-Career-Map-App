// Sidebar Tab Click Handler
document.addEventListener('DOMContentLoaded', function () {
    const sidebarTab = document.getElementById('sidebar-tab');
    const sidebar = document.getElementById('filter-sidebar');
    const backdrop = document.getElementById('sidebar-backdrop');

    if (sidebarTab && sidebar && backdrop) {
        sidebarTab.addEventListener('click', function () {
            if (sidebar.classList.contains('open')) {
                sidebar.classList.remove('open');
                backdrop.classList.remove('show');
            } else {
                sidebar.classList.add('open');
                backdrop.classList.add('show');
            }
        });

        // Close sidebar when clicking backdrop
        backdrop.addEventListener('click', function () {
            sidebar.classList.remove('open');
            backdrop.classList.remove('show');
        });
    }
});
