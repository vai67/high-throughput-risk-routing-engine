// Urban Mobility Risk Engine - Frontend JavaScript

const API_BASE_URL = 'http://localhost:5000';

// Application state
const state = {
    map: null,
    startMarker: null,
    endMarker: null,
    routeLayer: null,
    heatmapLayer: null,
    trafficMarkers: [],
    crimeMarkers: [],
    startCoords: null,
    endCoords: null,
    selectingStart: false,
    selectingEnd: false
};


document.addEventListener('DOMContentLoaded', () => {
    initializeMap();
    setupEventListeners();
    checkAPIStatus();
});


function initializeMap() {
    // Default center (Louisville, KY)
    state.map = L.map('map').setView([38.2527, -85.7585], 12);
    
    //  OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(state.map);
    
    //  map click handler
    state.map.on('click', handleMapClick);
    
    //  custom controls
    addLegend();
}

//  event listeners
function setupEventListeners() {
    // Location input focus handlers
    document.getElementById('startInput').addEventListener('focus', () => {
        state.selectingStart = true;
        state.selectingEnd = false;
        document.getElementById('startInput').placeholder = 'Click on map to select';
    });
    
    document.getElementById('endInput').addEventListener('focus', () => {
        state.selectingStart = false;
        state.selectingEnd = true;
        document.getElementById('endInput').placeholder = 'Click on map to select';
    });
    
    // Preference sliders
    const sliders = ['speed', 'safety', 'weather', 'crime'];
    sliders.forEach(slider => {
        const element = document.getElementById(`${slider}Pref`);
        element.addEventListener('input', (e) => {
            document.getElementById(`${slider}Value`).textContent = `${e.target.value}%`;
        });
    });
    
    // Action buttons
    document.getElementById('calculateBtn').addEventListener('click', calculateRoute);
    document.getElementById('clearBtn').addEventListener('click', clearAll);
    
    // View options
    document.getElementById('showHeatmap').addEventListener('change', toggleHeatmap);
    document.getElementById('showTraffic').addEventListener('change', toggleTraffic);
    document.getElementById('showCrime').addEventListener('change', toggleCrime);
}

//  map clicks
function handleMapClick(e) {
    const { lat, lng } = e.latlng;
    
    if (state.selectingStart) {
        setStartLocation(lat, lng);
        state.selectingStart = false;
        document.getElementById('startInput').placeholder = 'Enter start address or click map';
    } else if (state.selectingEnd) {
        setEndLocation(lat, lng);
        state.selectingEnd = false;
        document.getElementById('endInput').placeholder = 'Enter end address or click map';
    }
}

//  start location
function setStartLocation(lat, lon) {
    state.startCoords = { lat, lon };
    
    // remove existing marker
    if (state.startMarker) {
        state.map.removeLayer(state.startMarker);
    }
    
    // Add new marker
    state.startMarker = L.marker([lat, lon], {
        icon: createCustomIcon('green')
    }).addTo(state.map);
    
    // Update UI
    document.getElementById('startCoords').textContent = `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
    document.getElementById('startInput').value = `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
}

// Set end location
function setEndLocation(lat, lon) {
    state.endCoords = { lat, lon };
    
    // Remove existing marker
    if (state.endMarker) {
        state.map.removeLayer(state.endMarker);
    }
    
    // Add new marker
    state.endMarker = L.marker([lat, lon], {
        icon: createCustomIcon('red')
    }).addTo(state.map);
    
    // Update UI
    document.getElementById('endCoords').textContent = `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
    document.getElementById('endInput').value = `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
}


function createCustomIcon(color) {
    return L.divIcon({
        className: 'custom-marker',
        html: `<div style="
            background: ${color};
            width: 30px;
            height: 30px;
            border-radius: 50%;
            border: 3px solid white;
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        "></div>`,
        iconSize: [30, 30],
        iconAnchor: [15, 15]
    });
}

// Calculate route
async function calculateRoute() {
    if (!state.startCoords || !state.endCoords) {
        alert('Please select both start and end locations');
        return;
    }
    
    
    document.getElementById('loadingOverlay').style.display = 'flex';
    
    try {
        // Get preferences
        const preferences = {
            speed: parseFloat(document.getElementById('speedPref').value) / 100,
            safety: parseFloat(document.getElementById('safetyPref').value) / 100,
            weather: parseFloat(document.getElementById('weatherPref').value) / 100,
            crime: parseFloat(document.getElementById('crimePref').value) / 100
        };
        
        // Make API request
        const response = await fetch(`${API_BASE_URL}/api/route`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                start: state.startCoords,
                end: state.endCoords,
                preferences: preferences
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to calculate route');
        }
        
        const data = await response.json();
        
        
        displayRoute(data);
        updateResults(data);
        document.getElementById('resultsPanel').style.display = 'block';
        
    } catch (error) {
        console.error('Error calculating route:', error);
        alert('Failed to calculate route. Please try again.');
    } finally {
        document.getElementById('loadingOverlay').style.display = 'none';
    }
}


function displayRoute(data) {
    
    if (state.routeLayer) {
        state.map.removeLayer(state.routeLayer);
    }
    
    
    const routeCoords = data.route.map(point => [point[0], point[1]]);
    
    
    const color = getRiskColor(data.risk_score);
    
    state.routeLayer = L.polyline(routeCoords, {
        color: color,
        weight: 6,
        opacity: 0.7
    }).addTo(state.map);
    
    
    state.map.fitBounds(state.routeLayer.getBounds(), { padding: [50, 50] });
    
    
    addRiskMarkers(data);
}

// Update results panel
function updateResults(data) {
    // Overall risk score
    document.getElementById('overallRisk').textContent = data.risk_score.toFixed(1);
    document.getElementById('riskLevel').textContent = data.risk_breakdown.risk_level + ' Risk';
    
    // Change color based on risk level
    const scoreElement = document.getElementById('overallRisk');
    scoreElement.style.color = getRiskColor(data.risk_score);
    
    // Route metrics
    document.getElementById('distanceValue').textContent = `${data.distance} km`;
    document.getElementById('timeValue').textContent = `${data.estimated_time} min`;
    
    // Risk breakdown
    updateRiskBar('traffic', data.risk_breakdown.traffic_risk);
    updateRiskBar('crime', data.risk_breakdown.crime_risk);
    updateRiskBar('weather', data.risk_breakdown.weather_risk);
    
    document.getElementById('trafficRisk').textContent = data.risk_breakdown.traffic_risk.toFixed(1);
    document.getElementById('crimeRiskValue').textContent = data.risk_breakdown.crime_risk.toFixed(1);
    document.getElementById('weatherRiskValue').textContent = data.risk_breakdown.weather_risk.toFixed(1);
    
    // Warnings
    displayWarnings(data.warnings);
}

// Update risk bar
function updateRiskBar(type, value) {
    const bar = document.getElementById(`${type}Bar`);
    bar.style.width = `${value}%`;
}

// Display warnings
function displayWarnings(warnings) {
    const container = document.getElementById('warningsContainer');
    
    if (warnings.length === 0) {
        container.innerHTML = '<div style="color: #10b981; font-weight: 500;">✓ No warnings for this route</div>';
        return;
    }
    
    container.innerHTML = warnings.map(warning => `
        <div class="warning-item">${warning}</div>
    `).join('');
}

// Get color based on risk score
function getRiskColor(score) {
    if (score >= 75) return '#ef4444';  // Red
    if (score >= 50) return '#f59e0b';  // Orange
    if (score >= 30) return '#eab308';  // Yellow
    return '#10b981';  // Green
}


function addRiskMarkers(data) {

    const route = data.route;
    const segmentSize = Math.floor(route.length / 5);
    
    for (let i = 1; i < 5; i++) {
        const point = route[i * segmentSize];
        const marker = L.circleMarker([point[0], point[1]], {
            radius: 5,
            fillColor: getRiskColor(data.risk_score),
            color: '#fff',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.8
        }).addTo(state.map);
        
        marker.bindPopup(`
            <div style="padding: 10px;">
                <strong>Segment Risk: ${data.risk_score.toFixed(1)}</strong><br>
                <small>Traffic: ${data.risk_breakdown.traffic_risk.toFixed(1)}</small><br>
                <small>Crime: ${data.risk_breakdown.crime_risk.toFixed(1)}</small><br>
                <small>Weather: ${data.risk_breakdown.weather_risk.toFixed(1)}</small>
            </div>
        `);
    }
}

// Toggle heatmap
async function toggleHeatmap(e) {
    if (e.target.checked) {
        await loadHeatmap();
    } else {
        if (state.heatmapLayer) {
            state.map.removeLayer(state.heatmapLayer);
        }
    }
}

// Load and display risk heatmap
async function loadHeatmap() {
    try {
        const center = state.map.getCenter();
        
        const response = await fetch(`${API_BASE_URL}/api/risk-heatmap`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                center: { lat: center.lat, lon: center.lng },
                radius_km: 5,
                grid_size: 20
            })
        });
        
        const data = await response.json();
        
        // Convert to heatmap format
        const heatData = data.data.map(point => [
            point.lat,
            point.lon,
            point.risk / 100  // Normalize to 0-1
        ]);
        
        // Remove existing heatmap
        if (state.heatmapLayer) {
            state.map.removeLayer(state.heatmapLayer);
        }
        
        // Add new heatmap
        state.heatmapLayer = L.heatLayer(heatData, {
            radius: 25,
            blur: 15,
            maxZoom: 17,
            max: 1.0,
            gradient: {
                0.0: '#10b981',
                0.3: '#eab308',
                0.5: '#f59e0b',
                0.7: '#ef4444',
                1.0: '#dc2626'
            }
        }).addTo(state.map);
        
    } catch (error) {
        console.error('Error loading heatmap:', error);
    }
}

// Toggle traffic display
function toggleTraffic(e) {
    // In production, this would show/hide real traffic data
    console.log('Traffic toggle:', e.target.checked);
}

// Toggle crime display
function toggleCrime(e) {
    // In production, this would show/hide crime incidents
    console.log('Crime toggle:', e.target.checked);
}

// Clear all
function clearAll() {
    // Remove markers
    if (state.startMarker) state.map.removeLayer(state.startMarker);
    if (state.endMarker) state.map.removeLayer(state.endMarker);
    if (state.routeLayer) state.map.removeLayer(state.routeLayer);
    if (state.heatmapLayer) state.map.removeLayer(state.heatmapLayer);
    
    // Reset state
    state.startCoords = null;
    state.endCoords = null;
    state.startMarker = null;
    state.endMarker = null;
    state.routeLayer = null;
    
    // Clear UI
    document.getElementById('startInput').value = '';
    document.getElementById('endInput').value = '';
    document.getElementById('startCoords').textContent = '—';
    document.getElementById('endCoords').textContent = '—';
    
    // Hide results
    document.getElementById('resultsPanel').style.display = 'none';
    
    // Reset map view
    state.map.setView([38.2527, -85.7585], 12);
}

//  legend to map
function addLegend() {
    const legend = L.control({ position: 'bottomright' });
    
    legend.onAdd = function(map) {
        const div = L.DomUtil.create('div', 'legend');
        div.style.cssText = `
            background: white;
            padding: 10px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        `;
        
        div.innerHTML = `
            <div style="font-weight: bold; margin-bottom: 5px;">Risk Level</div>
            <div><span style="color: #10b981;">●</span> Low (0-30)</div>
            <div><span style="color: #eab308;">●</span> Moderate (30-50)</div>
            <div><span style="color: #f59e0b;">●</span> High (50-75)</div>
            <div><span style="color: #ef4444;">●</span> Very High (75+)</div>
        `;
        
        return div;
    };
    
    legend.addTo(state.map);
}

// Check API status
async function checkAPIStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();
        
        if (data.status === 'healthy') {
            console.log('API is online');
        }
    } catch (error) {
        console.warn('API is not available. Using demo mode.');
        document.getElementById('statusBadge').innerHTML = 
            '<i class="fas fa-circle" style="color: #f59e0b;"></i> Demo Mode';
    }
}

// Utility function to format numbers
function formatNumber(num, decimals = 2) {
    return num.toFixed(decimals);
}