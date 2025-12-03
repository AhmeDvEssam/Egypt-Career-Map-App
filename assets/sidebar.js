// Sidebar Tab Click Handler - Works with Dash dynamic loading
document.addEventListener('DOMContentLoaded', function () {
    console.log('DOM loaded, initializing sidebar...');

    function initSidebar() {
        const sidebarTab = document.getElementById('sidebar-tab');
        const sidebar = document.getElementById('filter-sidebar');
        const backdrop = document.getElementById('sidebar-backdrop');

        console.log('Sidebar elements:', {
            sidebarTab: sidebarTab,
            sidebar: sidebar,
            backdrop: backdrop
        });

        if (sidebarTab && sidebar && backdrop) {
            // Add click handler to sidebar tab
            sidebarTab.addEventListener('click', function () {
                console.log('Sidebar tab clicked!');
                if (sidebar.classList.contains('open')) {
                    sidebar.classList.remove('open');
                    backdrop.classList.remove('show');
                    console.log('Sidebar closed');
                } else {
                    sidebar.classList.add('open');
                    backdrop.classList.add('show');
                    console.log('Sidebar opened');
                }
            });

            // Close sidebar when clicking backdrop
            backdrop.addEventListener('click', function () {
                console.log('Backdrop clicked!');
                sidebar.classList.remove('open');
                backdrop.classList.remove('show');
            });

            console.log('Sidebar initialized successfully!');
            return true;
        } else {
            console.log('Sidebar elements not found yet');
            return false;
        }
    }

    // Try to initialize immediately
    setTimeout(initSidebar, 100);

    // Also try periodically in case Dash loads content later
    let attempts = 0;
    const maxAttempts = 50;
    const interval = setInterval(function () {
        if (initSidebar() || attempts++ > maxAttempts) {
            clearInterval(interval);
            if (attempts > maxAttempts) {
                console.error('Failed to initialize sidebar after max attempts');
            }
        }
    }, 200);
});
