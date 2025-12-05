// Theme Switcher - Clientside Callback
// This runs in the browser to apply theme CSS classes

window.dash_clientside = Object.assign({}, window.dash_clientside, {
    clientside: {
        apply_theme: function (theme) {
            // Apply theme class to body
            const body = document.body;

            if (theme === 'dark') {
                body.classList.remove('light-mode');
                body.classList.add('dark-mode');
                console.log('Applied dark theme');
            } else {
                body.classList.remove('dark-mode');
                body.classList.add('light-mode');
                console.log('Applied light theme');
            }

            // Return the theme to satisfy callback output
            return theme;
        }
    }
});
