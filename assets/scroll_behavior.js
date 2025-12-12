
// Auto-hide popup when it collides with the Map
// Helps avoid double tooltips overlap

document.addEventListener('DOMContentLoaded', function () {
    window.addEventListener('scroll', function () {
        var popup = document.getElementById('click-popup');
        var map = document.getElementById('map-wrapper');

        if (!popup || !map) return;

        // Optimization: Only check if popup is actually visible
        if (popup.style.display === 'none') return;

        var popupRect = popup.getBoundingClientRect();
        var mapRect = map.getBoundingClientRect();

        // Logic: 
        // If the Bottom of the Map (which moves up/down with scroll)
        // extends BELOW the Top of the Popup (which is fixed at bottom),
        // then they are overlapping (or Map is taking over).

        // mapRect.bottom is the Y coordinate of the map's bottom edge relative to viewport.
        // popupRect.top is the Y coordinate of the popup's top edge relative to viewport.

        // If mapRect.bottom > popupRect.top, the map is drawing "over" the popup area.
        if (mapRect.bottom > popupRect.top + 10) { // +10 buffer
            popup.style.display = 'none';
        }
    }, { passive: true });
});
