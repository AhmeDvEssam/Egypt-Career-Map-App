# 📊 Hire Q Services - Jobs Dashboard

> **Professional SaaS-grade dashboard for analyzing the Egyptian job market**

A comprehensive, interactive data visualization platform built with Python Dash, featuring real-time job market analytics, advanced filtering, and beautiful visualizations for the Egyptian job market.

![Dashboard Preview](https://img.shields.io/badge/Status-Production%20Ready-success)
![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Dash](https://img.shields.io/badge/Dash-2.0+-orange)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Features

### 📈 **5 Interactive Pages**
- **Overview** - High-level KPIs and market trends
- **City Map** - Geographic distribution with interactive maps
- **Deep Analysis** - Detailed company and category insights
- **Time Analysis** - Temporal trends and posting patterns
- **Skills Analysis** - In-demand skills and requirements

### 🎯 **22 Professional KPIs**
- Real-time metrics with Font Awesome icons
- Animated cards with hover effects
- Automatic calculations from filtered data
- Formatted numbers with commas and percentages

### 🔍 **Advanced Filtering**
- Multi-select filters (Company, City, Category, etc.)
- Date range picker
- Experience level slider
- Global search across all fields
- Click-to-filter on charts

### 🎨 **Modern Design System**
- Professional SaaS-grade UI
- Unified color palette (#003A70, #0066CC, #00CCFF)
- Responsive design (Mobile, Tablet, Desktop)
- Dark mode support
- Print-friendly layouts

### 📊 **Interactive Visualizations**
- Horizontal bar charts with gradients
- Donut/pie charts
- Word clouds (treemap)
- Time series analysis
- Geographic heatmaps

---

## 🚀 Quick Start

### Prerequisites
```bash
Python 3.8+
pip (Python package manager)
```

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/hire-q-dashboard.git
cd hire-q-dashboard
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Prepare your data**
   - Place `Jobs.xlsx` in the project root
   - Place `Skills_Cleaned_UnPivot.xlsx` in the project root

4. **Run the application**
```bash
python DashApp.py
```

5. **Open in browser**
```
http://127.0.0.1:8050
```

---

## 📁 Project Structure

```
hire-q-dashboard/
│
├── DashApp.py                 # Main application file
├── Jobs.xlsx                  # Jobs dataset
├── Skills_Cleaned_UnPivot.xlsx # Skills dataset
├── requirements.txt           # Python dependencies
│
├── assets/                    # Static assets
│   ├── custom.css            # Main stylesheet
│   ├── design_tokens.css     # Design system variables
│   ├── kpi_cards.css         # KPI component styles
│   ├── charts.css            # Chart wrapper styles
│   ├── responsive.css        # Responsive breakpoints
│   ├── deep_analysis_filters.js  # Click-to-filter logic
│   └── click_filters.js      # Filter interactions
│
└── README.md                  # This file
```

---

## 🎨 Design System

### Color Palette
- **Primary Dark**: `#003A70`
- **Primary Medium**: `#0066CC`
- **Primary Light**: `#00CCFF`
- **Background**: `#F8F9FA`
- **Card Background**: `#FFFFFF`

### Typography
- **Font Family**: Inter (Google Fonts)
- **Sizes**: 12px - 32px scale
- **Weights**: 400 (Regular), 600 (Semibold), 700 (Bold)

### Spacing
- **Base Unit**: 8px
- **Scale**: 8px, 16px, 24px, 32px, 40px, 48px

---

## 📊 Data Requirements

### Jobs.xlsx
Required columns:
- `Jobs Title` / `Job Title`
- `Company`
- `City`, `In_City`, `Location`
- `Category`
- `Employment Type`
- `Work Mode`
- `Career Level`
- `education_level`
- `Year Of Exp_Avg`
- `applicants`
- `Date_Posted` / `posted`
- `Latitude`, `Longitude` (optional)

### Skills_Cleaned_UnPivot.xlsx
Required columns:
- `Job Title`
- `Skills`

---

## 🔧 Configuration

### Environment Variables
```bash
# Optional: Enable auto-geocoding for missing coordinates
export AUTO_GEOCODE=1
```

### Map Styles
Available map styles in City Map page:
- Voyager (Light)
- Dark Matter (Dark)
- Satellite (Esri)
- Positron (Light Grey)
- OpenStreetMap

---

## 📱 Responsive Breakpoints

- **Mobile**: `< 768px` - Single column, overlay sidebar
- **Tablet**: `768px - 1200px` - 2-column layout
- **Desktop**: `> 1200px` - Full multi-column layout

---

## 🎯 Key Features Breakdown

### Overview Page
- Total Jobs, Companies, Categories
- Average Applicants per Job
- % Remote/Hybrid Jobs
- Latest Posting Date
- Employment Type distribution
- Work Mode breakdown
- Career Level analysis
- Top 10 Categories

### Deep Analysis Page
- Top Companies by Applicants
- Education Requirements
- Career Level vs Experience
- Experience Level Demand
- Hiring Intensity by Company

### Time Analysis Page
- Jobs in selected period
- Month-over-Month growth
- Average Applicants trend
- Peak posting day of week
- Monthly distribution
- Daily patterns

### Skills Analysis Page
- Total unique skills
- Most demanded skill
- Average skills per job
- Top skill category
- Skills word cloud (Top 30)
- Skills by category breakdown
- Skills demand trend over time

### City Map Page
- Interactive map with job locations
- Jobs by city (bar chart)
- Clickable markers with job details
- Multiple map style options
- Data table with job listings

---

## 🛠️ Technologies Used

- **Backend**: Python 3.8+
- **Framework**: Dash 2.0+, Plotly
- **UI Components**: Dash Bootstrap Components
- **Maps**: Folium, Leaflet.js
- **Data Processing**: Pandas, NumPy
- **Styling**: CSS3, Font Awesome 6
- **Fonts**: Inter (Google Fonts)

---

## 📈 Performance

- **Load Time**: < 2 seconds
- **Animations**: 60 FPS (GPU-accelerated)
- **Data Handling**: Optimized for 7000+ records
- **Responsive**: Smooth on all devices

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**Ahmed Essam Eldin Hamed**

-LinkedIn:https://www.linkedin.com/in/ahmed-essam-%F0%9F%87%B5%F0%9F%87%B8-18a075218/
- Email: ahmed.essam.eldinn@gmail.com

---

## 🙏 Acknowledgments

- Data sourced from Wuzzuf.com
- Icons by Font Awesome
- Maps by Leaflet.js and OpenStreetMap
- UI inspired by modern SaaS dashboards

---

## 📸 Screenshots

### Overview Page
![Overview](screenshots/overview.png)

### Deep Analysis
![Deep Analysis](screenshots/deep-analysis.png)

### City Map
![City Map](screenshots/city-map.png)

### Skills Analysis
![Skills](screenshots/skills.png)

---

## 🔮 Future Enhancements

- [ ] Real-time data updates
- [ ] Export to PDF/Excel
- [ ] User authentication
- [ ] Saved filter presets
- [ ] Email alerts for new jobs
- [ ] API integration
- [ ] Multi-language support (Arabic/English)

---

**⭐ If you find this project useful, please consider giving it a star!**
