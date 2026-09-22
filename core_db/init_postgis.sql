-- Enable PostGIS and pgvector extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;

-- Table for storing marine observation points (SST, Currents, PFZ)
CREATE TABLE IF NOT EXISTS marine_observations (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    sea_surface_temp NUMERIC(4,2),
    current_speed NUMERIC(4,2),
    pfz_score VARCHAR(20),
    geom GEOMETRY(Point, 4326)
);

-- Spatial index on geometry column for fast geospatial queries
CREATE INDEX IF NOT EXISTS idx_marine_obs_geom 
ON marine_observations USING GIST (geom);

-- Table for storing vector embeddings of maritime advisories / policy docs
CREATE TABLE IF NOT EXISTS advisory_embeddings (
    id SERIAL PRIMARY KEY,
    title TEXT,
    content TEXT,
    embedding VECTOR(1536)
);