-- Urban Mobility Risk Engine Database Schema
-- PostgreSQL with PostGIS extension

-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- Create schema
CREATE SCHEMA IF NOT EXISTS urban_mobility;

-- Set search path
SET search_path TO urban_mobility, public;

-- Traffic Data Table
CREATE TABLE traffic_data (
    id SERIAL PRIMARY KEY,
    location GEOMETRY(Point, 4326) NOT NULL,
    congestion_level DECIMAL(3,2) CHECK (congestion_level >= 0 AND congestion_level <= 1),
    speed_kmh DECIMAL(5,2),
    incident_count INTEGER DEFAULT 0,
    incident_type VARCHAR(50),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(50),
    
    -- Spatial index
    CONSTRAINT valid_location CHECK (ST_IsValid(location))
);

CREATE INDEX idx_traffic_location ON traffic_data USING GIST(location);
CREATE INDEX idx_traffic_timestamp ON traffic_data(timestamp DESC);

-- Weather Data Table
CREATE TABLE weather_data (
    id SERIAL PRIMARY KEY,
    location GEOMETRY(Point, 4326) NOT NULL,
    temperature DECIMAL(5,2),
    precipitation DECIMAL(5,2),
    visibility INTEGER,
    wind_speed DECIMAL(5,2),
    condition VARCHAR(50),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(50),
    
    CONSTRAINT valid_weather_location CHECK (ST_IsValid(location))
);

CREATE INDEX idx_weather_location ON weather_data USING GIST(location);
CREATE INDEX idx_weather_timestamp ON weather_data(timestamp DESC);

-- Crime Data Table
CREATE TABLE crime_incidents (
    id SERIAL PRIMARY KEY,
    incident_id VARCHAR(100) UNIQUE,
    location GEOMETRY(Point, 4326) NOT NULL,
    crime_type VARCHAR(50) NOT NULL,
    severity DECIMAL(3,2) CHECK (severity >= 0 AND severity <= 1),
    incident_date TIMESTAMP WITH TIME ZONE NOT NULL,
    reported_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    
    CONSTRAINT valid_crime_location CHECK (ST_IsValid(location))
);

CREATE INDEX idx_crime_location ON crime_incidents USING GIST(location);
CREATE INDEX idx_crime_date ON crime_incidents(incident_date DESC);
CREATE INDEX idx_crime_type ON crime_incidents(crime_type);

-- Route History Table (for analytics)
CREATE TABLE route_history (
    id SERIAL PRIMARY KEY,
    start_point GEOMETRY(Point, 4326) NOT NULL,
    end_point GEOMETRY(Point, 4326) NOT NULL,
    route_path GEOMETRY(LineString, 4326),
    distance_km DECIMAL(10,2),
    estimated_time_minutes DECIMAL(10,2),
    risk_score DECIMAL(5,2),
    traffic_risk DECIMAL(5,2),
    crime_risk DECIMAL(5,2),
    weather_risk DECIMAL(5,2),
    user_preferences JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_route_start ON route_history USING GIST(start_point);
CREATE INDEX idx_route_end ON route_history USING GIST(end_point);
CREATE INDEX idx_route_timestamp ON route_history(timestamp DESC);

-- Risk Zones Table (pre-calculated high-risk areas)
CREATE TABLE risk_zones (
    id SERIAL PRIMARY KEY,
    zone_name VARCHAR(100),
    boundary GEOMETRY(Polygon, 4326) NOT NULL,
    risk_level VARCHAR(20) CHECK (risk_level IN ('low', 'moderate', 'high', 'very_high')),
    risk_score DECIMAL(5,2),
    primary_factor VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_zone_boundary CHECK (ST_IsValid(boundary))
);

CREATE INDEX idx_risk_zones_boundary ON risk_zones USING GIST(boundary);
CREATE INDEX idx_risk_zones_level ON risk_zones(risk_level);

-- User Feedback Table (for improving the system)
CREATE TABLE user_feedback (
    id SERIAL PRIMARY KEY,
    route_id INTEGER REFERENCES route_history(id),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    accuracy_score INTEGER CHECK (accuracy_score >= 1 AND accuracy_score <= 5),
    feedback_text TEXT,
    actual_time_minutes DECIMAL(10,2),
    issues_encountered TEXT[],
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_feedback_route ON user_feedback(route_id);
CREATE INDEX idx_feedback_timestamp ON user_feedback(timestamp DESC);

-- Views for Analytics

-- Recent Traffic Summary
CREATE OR REPLACE VIEW recent_traffic_summary AS
SELECT 
    ST_AsGeoJSON(location)::json AS location,
    AVG(congestion_level) AS avg_congestion,
    AVG(speed_kmh) AS avg_speed,
    COUNT(*) AS reading_count,
    MAX(timestamp) AS last_updated
FROM traffic_data
WHERE timestamp > NOW() - INTERVAL '1 hour'
GROUP BY ST_SnapToGrid(location, 0.01);

-- Crime Hotspots (last 30 days)
CREATE OR REPLACE VIEW crime_hotspots AS
SELECT 
    ST_AsGeoJSON(ST_Centroid(ST_Collect(location)))::json AS center,
    COUNT(*) AS incident_count,
    AVG(severity) AS avg_severity,
    ARRAY_AGG(DISTINCT crime_type) AS crime_types
FROM crime_incidents
WHERE incident_date > NOW() - INTERVAL '30 days'
GROUP BY ST_SnapToGrid(location, 0.01)
HAVING COUNT(*) >= 3
ORDER BY incident_count DESC;

-- Route Risk Summary
CREATE OR REPLACE VIEW route_risk_summary AS
SELECT 
    DATE(timestamp) AS date,
    COUNT(*) AS routes_calculated,
    AVG(risk_score) AS avg_risk,
    AVG(traffic_risk) AS avg_traffic_risk,
    AVG(crime_risk) AS avg_crime_risk,
    AVG(weather_risk) AS avg_weather_risk,
    AVG(distance_km) AS avg_distance
FROM route_history
GROUP BY DATE(timestamp)
ORDER BY date DESC;

-- Stored Procedures

-- Function to find nearby traffic data
CREATE OR REPLACE FUNCTION get_nearby_traffic(
    p_lat DECIMAL,
    p_lon DECIMAL,
    p_radius_km DECIMAL DEFAULT 2.0
)
RETURNS TABLE (
    distance_km DECIMAL,
    congestion_level DECIMAL,
    speed_kmh DECIMAL,
    incident_count INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ROUND(ST_Distance(
            location::geography,
            ST_SetSRID(ST_MakePoint(p_lon, p_lat), 4326)::geography
        ) / 1000, 2) AS distance_km,
        t.congestion_level,
        t.speed_kmh,
        t.incident_count,
        t.timestamp
    FROM traffic_data t
    WHERE ST_DWithin(
        location::geography,
        ST_SetSRID(ST_MakePoint(p_lon, p_lat), 4326)::geography,
        p_radius_km * 1000
    )
    AND timestamp > NOW() - INTERVAL '1 hour'
    ORDER BY distance_km;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate crime density in area
CREATE OR REPLACE FUNCTION calculate_crime_density(
    p_lat DECIMAL,
    p_lon DECIMAL,
    p_radius_km DECIMAL DEFAULT 1.0
)
RETURNS TABLE (
    incident_count INTEGER,
    avg_severity DECIMAL,
    density_per_km2 DECIMAL
) AS $$
DECLARE
    v_area_km2 DECIMAL;
BEGIN
    v_area_km2 := PI() * p_radius_km * p_radius_km;
    
    RETURN QUERY
    SELECT 
        COUNT(*)::INTEGER AS incident_count,
        ROUND(AVG(severity), 2) AS avg_severity,
        ROUND(COUNT(*) / v_area_km2, 2) AS density_per_km2
    FROM crime_incidents
    WHERE ST_DWithin(
        location::geography,
        ST_SetSRID(ST_MakePoint(p_lon, p_lat), 4326)::geography,
        p_radius_km * 1000
    )
    AND incident_date > NOW() - INTERVAL '90 days';
END;
$$ LANGUAGE plpgsql;

-- Function to log route calculation
CREATE OR REPLACE FUNCTION log_route(
    p_start_lat DECIMAL,
    p_start_lon DECIMAL,
    p_end_lat DECIMAL,
    p_end_lon DECIMAL,
    p_path_json JSON,
    p_distance DECIMAL,
    p_time DECIMAL,
    p_risk_score DECIMAL,
    p_traffic_risk DECIMAL,
    p_crime_risk DECIMAL,
    p_weather_risk DECIMAL,
    p_preferences JSONB
)
RETURNS INTEGER AS $$
DECLARE
    v_route_id INTEGER;
BEGIN
    INSERT INTO route_history (
        start_point,
        end_point,
        distance_km,
        estimated_time_minutes,
        risk_score,
        traffic_risk,
        crime_risk,
        weather_risk,
        user_preferences
    ) VALUES (
        ST_SetSRID(ST_MakePoint(p_start_lon, p_start_lat), 4326),
        ST_SetSRID(ST_MakePoint(p_end_lon, p_end_lat), 4326),
        p_distance,
        p_time,
        p_risk_score,
        p_traffic_risk,
        p_crime_risk,
        p_weather_risk,
        p_preferences
    )
    RETURNING id INTO v_route_id;
    
    RETURN v_route_id;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update risk zones
CREATE OR REPLACE FUNCTION update_risk_zones_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_risk_zones
BEFORE UPDATE ON risk_zones
FOR EACH ROW
EXECUTE FUNCTION update_risk_zones_timestamp();

-- Indexes for performance
CREATE INDEX idx_traffic_recent ON traffic_data(timestamp) 
    WHERE timestamp > NOW() - INTERVAL '2 hours';

CREATE INDEX idx_crime_recent ON crime_incidents(incident_date) 
    WHERE incident_date > NOW() - INTERVAL '90 days';

-- Comments for documentation
COMMENT ON TABLE traffic_data IS 'Real-time traffic conditions and incidents';
COMMENT ON TABLE weather_data IS 'Current and historical weather conditions';
COMMENT ON TABLE crime_incidents IS 'Historical crime data for risk assessment';
COMMENT ON TABLE route_history IS 'Log of all calculated routes for analytics';
COMMENT ON TABLE risk_zones IS 'Pre-identified high-risk geographic areas';
COMMENT ON TABLE user_feedback IS 'User feedback on route accuracy and quality';
