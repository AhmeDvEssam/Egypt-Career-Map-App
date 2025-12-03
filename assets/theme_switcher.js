// Theme Switcher - Clientside Callback
// This runs in the browser to apply theme CSS classes

window.dash_clientside = Object.assign({}, window.dash_clientside, {
    clientside: {
        apply_theme: function (theme) {
            // Apply theme class to body
            const body = document.body;

            if (theme === 'dark') {
                body.classList.remove('light-theme');
                body.classList.add('dark-theme');
                console.log('Applied dark theme');
            } else {
                body.classList.remove('dark-theme');
                body.classList.add('light-theme');
                console.log('Applied light theme');
            }

            // Return the theme to satisfy callback output
            return theme;
        }
    }
});
