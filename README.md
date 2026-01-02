# Real-Time Urban Mobility Risk Engine

A sophisticated system that computes real-time risk scores for urban routes based on traffic, weather, crime data, and time of day.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![PostgreSQL](https://img.shields.io/badge/postgresql-14+-blue.svg)

# Project Overview

This project uses:
- **Real-time data ingestion** from multiple sources
- **Intelligent risk scoring** using weighted algorithms
- **Advanced pathfinding** with Dijkstra & A* algorithms
- **PostGIS spatial queries** for efficient geospatial operations
- **Interactive map visualization** with Leaflet
- **RESTful API** built with FastAPI
- **Production-ready architecture** with Docker

## Architecture:

┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend  │────▶│    FastAPI   │────▶│  PostgreSQL  │
│  (Leaflet)  │     │   Backend    │     │   + PostGIS  │
└─────────────┘     └──────────────┘     └──────────────┘
                           │
                           │
                    ┌──────┴──────┐
                    │             │
              ┌─────▼─────┐ ┌────▼─────┐
              │  Traffic  │ │  Weather │
              │   APIs    │ │   APIs   │
              └───────────┘ └──────────┘
                           │
                      ┌────▼─────┐
                      │  Crime   │
                      │   Data   │
                      └──────────┘


## Features:

## Core Functionality:
- **Multi-factor Risk Assessment**
  - Traffic congestion analysis
  - Crime density mapping
  - Weather hazard evaluation
  - Time-of-day risk patterns

- **Intelligent Routing**
  - A* pathfinding algorithm
  - Customizable preference weights
  - Alternative route suggestions
  - Real-time route optimization

- **Data Visualization**
  - Interactive map interface
  - Risk heatmaps
  - Route comparison
  - Live data indicators

### Technical Highlights
- Spatial queries with PostGIS
- Asynchronous data collection
- Risk scoring engine
- RESTful API design
- Docker containerization
- Real-time updates

## Quick Start:

### Prerequisites
- Python 3.9+
- PostgreSQL 14+ with PostGIS
- Docker & Docker Compose (optional)
- Node.js 16+ (for development)

### Docker Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/urban-mobility-risk-engine.git
cd urban-mobility-risk-engine

# Create .env file
cat > .env << EOF
WEATHER_API_KEY=your_openweathermap_key
MAPBOX_TOKEN=your_mapbox_token
EOF

# Start all services
docker-compose up -d

# Access the application
# Frontend: http://localhost:8080
# API: http://localhost:5000
# API Docs: http://localhost:5000/docs
```

#### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
DATABASE_URL=postgresql://postgres:password@localhost:5432/urban_mobility
WEATHER_API_KEY=your_key_here
EOF

# Run the server
python app.py
```

#### 3. Frontend Setup
```bash
cd frontend

# Serve with Python's HTTP server
python -m http.server 8080

# Or use any static file server
# npx serve .
```

## API Documentation

### Calculate Route
```http
POST /api/route
Content-Type: application/json

{
  "start": {"lat": 38.2527, "lon": -85.7585},
  "end": {"lat": 38.2280, "lon": -85.7490},
  "preferences": {
    "speed": 0.4,
    "safety": 0.3,
    "weather": 0.2,
    "crime": 0.1
  }
}
```

**Response:**
```json
{
  "route": [[38.2527, -85.7585], ...],
  "risk_score": 45.2,
  "distance": 8.3,
  "estimated_time": 15.5,
  "risk_breakdown": {
    "traffic_risk": 52.0,
    "crime_risk": 38.5,
    "weather_risk": 25.0,
    "time_of_day_risk": 15.0
  },
  "warnings": ["⚡ Moderate traffic delays likely"]
}
```

### Get Risk Heatmap
```http
POST /api/risk-heatmap
Content-Type: application/json

{
  "center": {"lat": 38.2527, "lon": -85.7585},
  "radius_km": 5.0,
  "grid_size": 20
}
```

### Get Live Data
```http
GET /api/live-data?lat=38.2527&lon=-85.7585
```

Full API documentation available at: `http://localhost:5000/docs`

## Configuration

### Risk Weights
Customize risk calculation in `backend/risk_engine.py`:


self.default_weights = {
    'traffic': 0.3,
    'crime': 0.25,
    'weather': 0.25,
    'time_of_day': 0.2
}


### Data Sources
Configure API keys in `.env`:

```env
# OpenWeatherMap (free tier: 60 calls/min)
WEATHER_API_KEY=your_key

# Mapbox (for advanced mapping features)
MAPBOX_TOKEN=your_token
```

### High-Risk Hours
Modify time-based risk in `backend/risk_engine.py`:

```python
self.high_risk_hours = [(22, 4)]  # 10 PM to 4 AM
```

## Testing

```bash
# Run backend tests
cd backend
pytest tests/

# Test API endpoints
curl http://localhost:5000/health

# Load test (optional)
ab -n 1000 -c 10 http://localhost:5000/health
```

## Database Schema

Key tables:
- `traffic_data` - Real-time traffic conditions
- `weather_data` - Weather observations
- `crime_incidents` - Historical crime data
- `route_history` - Calculated routes for analytics
- `risk_zones` - Pre-identified high-risk areas

## Data Source Integration

### Real APIs to Connect

#### Traffic Data
- **Google Maps Traffic API** - Real-time traffic
- **TomTom Traffic API** - Flow and incidents
- **HERE Traffic API** - Comprehensive traffic data
- **Waze API** - Community-reported incidents

#### Weather Data
- **OpenWeatherMap** - Free tier available
- **WeatherAPI.com** - Detailed forecasts
- **Tomorrow.io** - Hyperlocal weather

#### Crime Data
- **FBI Crime Data API** - National statistics
- **City Open Data Portals** - Local crime data
- **SpotCrime API** - Aggregated crime data


**Vaibhavi Srivastava**
- LinkedIn:  www.linkedin.com/in/vai-srivastava
- Email: vai.sriv12@gmail.com