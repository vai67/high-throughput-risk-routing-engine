import networkx as nx
import math
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime
import heapq

class RoutingEngine:
    """
    Pathfinding engine using Dijkstra and A* algorithms with risk-aware routing.
    """
    
    def __init__(self):
        self.graph = None
        self.grid_resolution = 0.005  # ~500m grid cells
        
    def find_optimal_route(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        preferences: Dict[str, float],
        traffic_data: Dict[str, Any],
        weather_data: Dict[str, Any],
        crime_data: Dict[str, Any],
        time: datetime
    ) -> Dict[str, Any]:
        """
        Find optimal route using A* with risk-aware cost function.
        """
        
        # Build or update graph based on current conditions
        graph = self._build_route_graph(start, end, traffic_data, crime_data)
        
        # Add edge weights based on risk factors
        self._apply_risk_weights(
            graph,
            preferences,
            traffic_data,
            weather_data,
            crime_data,
            time
        )
        
        # Find shortest path using A*
        try:
            path_nodes = nx.astar_path(
                graph,
                start,
                end,
                heuristic=self._heuristic,
                weight='cost'
            )
            
            # Convert to coordinate list
            path = list(path_nodes)
            
            # Calculate route metrics
            distance = self._calculate_path_distance(path)
            time_estimate = self._estimate_travel_time(path, traffic_data)
            
            return {
                'path': path,
                'distance': distance,
                'time': time_estimate,
                'nodes': len(path)
            }
            
        except nx.NetworkXNoPath:
            # Fallback to straight line if no path found
            return self._fallback_route(start, end)
    
    def find_alternative_routes(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        main_route: List[Tuple[float, float]],
        preferences: Dict[str, float],
        limit: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Find alternative routes that differ from the main route.
        """
        alternatives = []
        
        # Create graph without main route edges
        graph = self._build_route_graph(start, end, {}, {})
        
        # Remove edges that are in main route
        edges_to_remove = []
        for i in range(len(main_route) - 1):
            if graph.has_edge(main_route[i], main_route[i + 1]):
                edges_to_remove.append((main_route[i], main_route[i + 1]))
        
        graph.remove_edges_from(edges_to_remove)
        
        try:
            # Find alternative path
            alt_path = nx.shortest_path(graph, start, end, weight='cost')
            
            if alt_path and alt_path != main_route:
                distance = self._calculate_path_distance(alt_path)
                alternatives.append({
                    'path': alt_path,
                    'distance': distance,
                    'deviation': self._calculate_deviation(main_route, alt_path)
                })
        except:
            pass
        
        return alternatives[:limit]
    
    def _build_route_graph(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        traffic_data: Dict[str, Any],
        crime_data: Dict[str, Any]
    ) -> nx.Graph:
        """
        Build a graph representation of possible routes.
        Creates a grid-based graph in the bounding box of start/end.
        """
        graph = nx.Graph()
        
        # Calculate bounding box
        min_lat = min(start[0], end[0]) - 0.02
        max_lat = max(start[0], end[0]) + 0.02
        min_lon = min(start[1], end[1]) - 0.02
        max_lon = max(start[1], end[1]) + 0.02
        
        # Generate grid nodes
        lat = min_lat
        while lat <= max_lat:
            lon = min_lon
            while lon <= max_lon:
                node = (round(lat, 4), round(lon, 4))
                graph.add_node(node, pos=(lat, lon))
                lon += self.grid_resolution
            lat += self.grid_resolution
        
        # Add start and end nodes
        graph.add_node(start, pos=start)
        graph.add_node(end, pos=end)
        
        # Connect nodes (8-directional grid)
        for node in list(graph.nodes()):
            neighbors = self._get_neighbors(node, graph)
            for neighbor in neighbors:
                if not graph.has_edge(node, neighbor):
                    distance = self._euclidean_distance(node, neighbor)
                    graph.add_edge(node, neighbor, distance=distance, cost=distance)
        
        return graph
    
    def _get_neighbors(
        self,
        node: Tuple[float, float],
        graph: nx.Graph
    ) -> List[Tuple[float, float]]:
        """
        Get neighboring nodes in 8 directions.
        """
        neighbors = []
        directions = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1)
        ]
        
        for dlat, dlon in directions:
            neighbor_lat = round(node[0] + dlat * self.grid_resolution, 4)
            neighbor_lon = round(node[1] + dlon * self.grid_resolution, 4)
            neighbor = (neighbor_lat, neighbor_lon)
            
            if graph.has_node(neighbor):
                neighbors.append(neighbor)
        
        return neighbors
    
    def _apply_risk_weights(
        self,
        graph: nx.Graph,
        preferences: Dict[str, float],
        traffic_data: Dict[str, Any],
        weather_data: Dict[str, Any],
        crime_data: Dict[str, Any],
        time: datetime
    ):
        """
        Apply risk-based weights to graph edges.
        """
        for u, v, data in graph.edges(data=True):
            base_cost = data['distance']
            
            # Traffic penalty
            traffic_penalty = self._get_traffic_penalty(u, v, traffic_data)
            
            # Crime penalty
            crime_penalty = self._get_crime_penalty(u, v, crime_data)
            
            # Weather penalty (uniform across area)
            weather_penalty = self._get_weather_penalty(weather_data)
            
            # Time of day penalty
            time_penalty = self._get_time_penalty(time)
            
            # Combine penalties based on preferences
            total_penalty = (
                traffic_penalty * preferences.get('speed', 0.4) +
                crime_penalty * preferences.get('crime', 0.3) +
                weather_penalty * preferences.get('weather', 0.2) +
                time_penalty * 0.1
            )
            
            # Apply penalty to cost
            data['cost'] = base_cost * (1 + total_penalty)
    
    def _get_traffic_penalty(
        self,
        u: Tuple[float, float],
        v: Tuple[float, float],
        traffic_data: Dict[str, Any]
    ) -> float:
        """
        Calculate traffic penalty for an edge (0-2.0).
        """
        if not traffic_data:
            return 0.0
        
        congestion = traffic_data.get('congestion_level', 0)
        return congestion * 2.0  # Up to 200% penalty
    
    def _get_crime_penalty(
        self,
        u: Tuple[float, float],
        v: Tuple[float, float],
        crime_data: Dict[str, Any]
    ) -> float:
        """
        Calculate crime penalty for an edge (0-1.5).
        """
        if not crime_data or 'points' not in crime_data:
            return 0.0
        
        # Check for nearby crime incidents
        mid_point = ((u[0] + v[0]) / 2, (u[1] + v[1]) / 2)
        nearby_crimes = 0
        
        for crime in crime_data.get('points', []):
            distance = self._euclidean_distance(
                mid_point,
                (crime['lat'], crime['lon'])
            )
            if distance < 0.005:  # Within ~500m
                nearby_crimes += 1
        
        return min(nearby_crimes * 0.3, 1.5)
    
    def _get_weather_penalty(self, weather_data: Dict[str, Any]) -> float:
        """
        Calculate weather penalty (0-1.0).
        """
        if not weather_data:
            return 0.0
        
        penalty = 0.0
        
        # Precipitation penalty
        precip = weather_data.get('precipitation', 0)
        if precip > 5:
            penalty += 0.5
        elif precip > 2:
            penalty += 0.3
        
        # Visibility penalty
        visibility = weather_data.get('visibility', 10000)
        if visibility < 1000:
            penalty += 0.5
        
        return min(penalty, 1.0)
    
    def _get_time_penalty(self, time: datetime) -> float:
        """
        Calculate time of day penalty (0-0.5).
        """
        hour = time.hour
        
        if 22 <= hour or hour < 4:
            return 0.5  # Late night
        elif 6 <= hour < 9 or 17 <= hour < 20:
            return 0.3  # Rush hour
        else:
            return 0.0
    
    def _heuristic(self, u: Tuple[float, float], v: Tuple[float, float]) -> float:
        """
        A* heuristic function (Euclidean distance).
        """
        return self._euclidean_distance(u, v)
    
    def _euclidean_distance(
        self,
        point1: Tuple[float, float],
        point2: Tuple[float, float]
    ) -> float:
        """
        Calculate Euclidean distance between two points.
        """
        return math.sqrt(
            (point1[0] - point2[0]) ** 2 +
            (point1[1] - point2[1]) ** 2
        )
    
    def _calculate_path_distance(self, path: List[Tuple[float, float]]) -> float:
        """
        Calculate total distance of path in km.
        """
        total_distance = 0.0
        for i in range(len(path) - 1):
            total_distance += self._haversine_distance(
                path[i][0], path[i][1],
                path[i + 1][0], path[i + 1][1]
            )
        return round(total_distance, 2)
    
    def _haversine_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        Calculate great circle distance in km.
        """
        R = 6371  # Earth radius in km
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) ** 2)
        
        c = 2 * math.asin(math.sqrt(a))
        return R * c
    
    def _estimate_travel_time(
        self,
        path: List[Tuple[float, float]],
        traffic_data: Dict[str, Any]
    ) -> float:
        """
        Estimate travel time in minutes.
        """
        distance = self._calculate_path_distance(path)
        
        # Base speed (km/h)
        base_speed = 50
        
        # Adjust for traffic
        if traffic_data and 'speed_ratio' in traffic_data:
            speed_ratio = traffic_data['speed_ratio']
            adjusted_speed = base_speed * speed_ratio
        else:
            adjusted_speed = base_speed
        
        # Time in minutes
        time_hours = distance / adjusted_speed
        return round(time_hours * 60, 1)
    
    def _calculate_deviation(
        self,
        route1: List[Tuple[float, float]],
        route2: List[Tuple[float, float]]
    ) -> float:
        """
        Calculate how much two routes deviate from each other.
        """
        # Simple metric: percentage of non-overlapping segments
        route1_set = set(route1)
        route2_set = set(route2)
        
        overlap = len(route1_set & route2_set)
        total = len(route1_set | route2_set)
        
        return round((1 - overlap / total) * 100, 1) if total > 0 else 0
    
    def _fallback_route(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float]
    ) -> Dict[str, Any]:
 
        # Create 10 intermediate points
        path = []
        for i in range(11):
            t = i / 10
            lat = start[0] + t * (end[0] - start[0])
            lon = start[1] + t * (end[1] - start[1])
            path.append((round(lat, 4), round(lon, 4)))
        
        distance = self._haversine_distance(start[0], start[1], end[0], end[1])
        time_estimate = (distance / 50) * 60  # Assume 50 km/h
        
        return {
            'path': path,
            'distance': round(distance, 2),
            'time': round(time_estimate, 1),
            'nodes': len(path)
        }