# Map Enhancements - City Map Page

## New Features Added

### 1. **City Labels**
- Each city now displays a label directly on the map
- Labels are positioned above the city markers with a semi-transparent white background
- City names are clearly visible with black text and subtle borders for better readability
- Labels automatically avoid overlapping with marker positions (offset by 25 pixels downward)

### 2. **Colored Circles Sized by Job Count**
- Circle size is now proportional to the **total number of jobs** in each city
- Larger circles = more job opportunities
- Colors are automatically assigned based on job count using the **Viridis color scale**:
  - Yellow/Bright colors = High number of jobs
  - Purple/Dark colors = Low number of jobs
- A color bar legend shows the "Total Jobs" scale on the right side of the map
- Markers have white borders (opacity 0.8, width 2px) for better visibility

### 3. **Enhanced Interactivity**
- **Double-click on a circle**: Zooms in to zoom level 10, centering on that city
- **Double-click on the map background**: Resets zoom to level 5 with default center (Egypt center)
- Better hover information when you mouse over cities
- Map is optimized for touch and desktop interactions

### 4. **Visual Improvements**
- Map height increased to 550px for better viewing
- Map uses OpenStreetMap as the base layer
- Improved color scale (Viridis) that's perceptually uniform and accessible
- Display mode bar visible for additional map tools
- Info text added: "💡 Double-click on any circle to zoom in; double-click the map background to zoom out."

## Technical Implementation

### Map Creation (scatter_mapbox)
```
- Latitude/Longitude: City coordinates from geocode cache
- Size: Job count (Total Jobs) - max 60px
- Color: Job count - Viridis scale
- Hover: City name + job count
```

### City Labels
- Added as annotations using `map_fig.add_annotation()` for each city
- Semi-transparent background with subtle borders
- Positioned at map coordinates (Longitude, Latitude)

### Zoom Callback
- New callback function: `handle_map_click()`
- Listens to `city-map.clickData` events
- Returns `relayout_data` to trigger map zoom/pan animation
- Zoom level 10 for city-level detail, level 5 for country overview

## Usage Instructions

1. **Open the City Map page** in the Dash app
2. **Interact with the map**:
   - Hover over circles to see city name and job count
   - **Double-click on any circle** to zoom in on that city
   - **Double-click on empty map area** to zoom back out
   - Use mouse wheel to scroll zoom (standard Plotly behavior)
   - Drag to pan around the map
3. **Filter by date range, company, or category** using the controls above the map
4. **The bar chart** on the left shows job count per city for easy reference

## Browser Compatibility
- Works on all modern browsers (Chrome, Firefox, Safari, Edge)
- Touch-friendly for mobile/tablet use
- Zoom animations are smooth and responsive

## Notes
- All cities are populated from the geocode_cache.json file
- If a city is not found in the cache, it won't appear on the map
- To add new cities, set AUTO_GEOCODE=1 environment variable and restart the app
- The map uses Plotly's native click handling for optimal performance
