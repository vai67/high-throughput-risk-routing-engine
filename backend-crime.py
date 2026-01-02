import asyncio
import random
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta
import math

class CrimeDataCollector:
    """
    Collects crime data from various sources.
    In production, integrates with:
    - Police department open data portals
    - FBI Crime Data API
    - Local crime mapping services
    """
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = 3600  # 1 hour (crime data changes slowly)
        
    async def get_data_for_area(
        self,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float
    ) -> Dict[str, Any]:
        """
        Get crime data for a rectangular area between two points.
        """
        cache_key = f"{start_lat:.2f}_{start_lon:.2f}_{end_lat:.2f}_{end_lon:.2f}"
        
        # Check cache
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if (datetime.now() - timestamp).seconds < self.cache_duration:
                return cached_data
        
        # Generate crime data
        crime_data = self._generate_area_crime_data(
            start_lat, start_lon, end_lat, end_lon
        )
        
        # Cache the result
        self.cache[cache_key] = (crime_data, datetime.now())
        
        return crime_data
    
    async def get_recent_incidents(
        self,
        lat: float,
        lon: float,
        radius_km: float = 2.0
    ) -> Dict[str, Any]:
        """
        Get recent crime incidents near a point.
        """
        # Generate incidents within radius
        incidents = self._generate_incidents_near_point(lat, lon, radius_km)
        
        return {
            'center': {'lat': lat, 'lon': lon},
            'radius_km': radius_km,
            'incident_count': len(incidents),
            'incidents': incidents,
            'timestamp': datetime.now().isoformat()
        }
    
    async def get_heatmap_data(
        self,
        lat: float,
        lon: float,
        radius_km: float
    ) -> Dict[str, Any]:
        """
        Get crime data formatted for heatmap visualization.
        """
        incidents = self._generate_incidents_near_point(lat, lon, radius_km)
        
        # Convert to heatmap point format
        points = []
        for incident in incidents:
            points.append({
                'lat': incident['location']['lat'],
                'lon': incident['location']['lon'],
                'severity': self._get_crime_severity(incident['type'])
            })
        
        return {
            'points': points,
            'density': len(points) / (math.pi * radius_km ** 2),
            'timestamp': datetime.now().isoformat()
        }
    
    async def get_data_along_route(
        self,
        path: List[Tuple[float, float]]
    ) -> Dict[str, Any]:
        """
        Get crime data along a route path.
        """
        # Calculate bounding box
        lats = [p[0] for p in path]
        lons = [p[1] for p in path]
        
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        
        return await self.get_data_for_area(min_lat, min_lon, max_lat, max_lon)
    
    def _generate_area_crime_data(
        self,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float
    ) -> Dict[str, Any]:
        """
        Generate realistic crime data for an area.
        """
        # Calculate area
        area_km2 = self._calculate_area(start_lat, start_lon, end_lat, end_lon)
        
        # Crime density varies by area (urban areas have more reported crimes)
        base_density = random.uniform(5, 25)  # crimes per km² per month
        total_crimes = int(base_density * area_km2)
        
        # Generate individual crime points
        incidents = []
        for _ in range(total_crimes):
            lat = random.uniform(min(start_lat, end_lat), max(start_lat, end_lat))
            lon = random.uniform(min(start_lon, end_lon), max(start_lon, end_lon))
            
            incident = self._generate_crime_incident(lat, lon)
            incidents.append(incident)
        
        # Calculate statistics
        recent_count = sum(1 for i in incidents if self._is_recent(i['date'], days=30))
        severity_score = sum(self._get_crime_severity(i['type']) for i in incidents) / len(incidents) if incidents else 0
        
        return {
            'density': round(base_density, 2),
            'total_count': total_crimes,
            'recent_count': recent_count,
            'severity': round(severity_score, 2),
            'incidents': incidents[:50],  # Return max 50 for performance
            'area_km2': round(area_km2, 2),
            'timestamp': datetime.now().isoformat()
        }
    
    def _generate_incidents_near_point(
        self,
        lat: float,
        lon: float,
        radius_km: float
    ) -> List[Dict[str, Any]]:
        """
        Generate crime incidents within radius of a point.
        """
        area_km2 = math.pi * radius_km ** 2
        density = random.uniform(5, 25)
        incident_count = int(density * area_km2)
        
        incidents = []
        for _ in range(min(incident_count, 100)):  # Cap at 100
            # Random point within circle
            angle = random.uniform(0, 2 * math.pi)
            r = radius_km * math.sqrt(random.random())
            
            # Convert to lat/lon offset (approximate)
            dlat = (r * math.cos(angle)) / 111.0
            dlon = (r * math.sin(angle)) / (111.0 * math.cos(math.radians(lat)))
            
            incident_lat = lat + dlat
            incident_lon = lon + dlon
            
            incident = self._generate_crime_incident(incident_lat, incident_lon)
            incidents.append(incident)
        
        return incidents
    
    def _generate_crime_incident(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Generate a single crime incident with realistic attributes.
        """
        crime_types = [
            ('theft', 0.4),
            ('vandalism', 0.2),
            ('assault', 0.15),
            ('burglary', 0.12),
            ('vehicle_theft', 0.08),
            ('robbery', 0.05)
        ]
        
        # Weighted random selection
        types, weights = zip(*crime_types)
        crime_type = random.choices(types, weights=weights)[0]
        
        # Generate random date within last 90 days
        days_ago = random.randint(0, 90)
        crime_date = datetime.now() - timedelta(days=days_ago)
        
        # Time of day affects crime likelihood
        hour_weights = [1 if 22 <= h or h < 6 else 0.3 for h in range(24)]
        hour = random.choices(range(24), weights=hour_weights)[0]
        crime_time = crime_date.replace(hour=hour, minute=random.randint(0, 59))
        
        return {
            'id': f"crime_{random.randint(100000, 999999)}",
            'type': crime_type,
            'date': crime_time.isoformat(),
            'location': {
                'lat': round(lat, 6),
                'lon': round(lon, 6)
            },
            'severity': self._get_crime_severity(crime_type),
            'days_ago': days_ago
        }
    
    def _get_crime_severity(self, crime_type: str) -> float:
        """
        Get severity score for crime type (0-1 scale).
        """
        severity_map = {
            'theft': 0.3,
            'vandalism': 0.2,
            'assault': 0.8,
            'burglary': 0.6,
            'vehicle_theft': 0.5,
            'robbery': 0.9
        }
        return severity_map.get(crime_type, 0.5)
    
    def _is_recent(self, date_str: str, days: int) -> bool:
        """
        Check if a date is within the last N days.
        """
        crime_date = datetime.fromisoformat(date_str)
        return (datetime.now() - crime_date).days <= days
    
    def _calculate_area(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        Calculate approximate area of rectangle in km².
        """
        # Approximate km per degree
        lat_diff = abs(lat2 - lat1) * 111.0
        lon_diff = abs(lon2 - lon1) * 111.0 * math.cos(math.radians((lat1 + lat2) / 2))
        
        return lat_diff * lon_diff


# Integration guide for real crime data sources:
"""
FBI CRIME DATA API:
-------------------
Free access to national crime statistics
https://crime-data-explorer.fr.cloud.gov/pages/docApi

import aiohttp

url = "https://api.usa.gov/crime/fbi/sapi/api/agencies"
params = {'api_key': 'YOUR_API_KEY'}

async with aiohttp.ClientSession() as session:
    async with session.get(url, params=params) as response:
        data = await response.json()


CITY OPEN DATA PORTALS:
------------------------
Many cities provide open crime data:

Chicago: https://data.cityofchicago.org/
NYC: https://data.cityofnewyork.us/
LA: https://data.lacity.org/
SF: https://datasf.org/

Example (using Socrata API):
url = "https://data.cityofchicago.org/resource/crimes.json"
params = {
    '$where': f'within_circle(location, {lat}, {lon}, {radius_meters})',
    '$limit': 1000
}


SPOTCRIME API:
--------------
Aggregates crime data from multiple sources
https://spotcrime.com/

Commercial API with free tier available


CRIMEMAPPING.COM:
-----------------
Many police departments use this platform
May require individual city access


DATA.GOV:
---------
Federal crime statistics
https://catalog.data.gov/dataset?tags=crime


"""