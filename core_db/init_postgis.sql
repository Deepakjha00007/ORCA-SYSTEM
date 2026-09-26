-- Enable PostGIS spatial and pgvector extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. Marine Observation Points (SST, Chlorophyll, Currents, PFZ score)
CREATE TABLE IF NOT EXISTS marine_observations (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    sea_surface_temp NUMERIC(5,2),      -- °C from OISST / Oceansat-3
    chlorophyll_mg_m3 NUMERIC(5,2),     -- mg/m³ from Oceansat-3
    current_speed NUMERIC(5,2),         -- Knots
    pfz_score VARCHAR(20) DEFAULT 'LOW', -- 'HIGH', 'MEDIUM', 'LOW'
    geom GEOMETRY(Point, 4326)           -- WGS84 Spatial Geometry
);

-- Index for fast spatial bounding box & proximity queries
CREATE INDEX IF NOT EXISTS idx_marine_obs_geom 
ON marine_observations USING GIST (geom);

-- 2. EEZ / IMBL Prohibited Boundaries & GeoJSON Zones
CREATE TABLE IF NOT EXISTS maritime_boundaries (
    id SERIAL PRIMARY KEY,
    name VARCHAR(250) NOT NULL,
    boundary_type VARCHAR(100),         -- 'IMBL', 'EEZ', 'MPA'
    geom GEOMETRY(MultiPolygon, 4326)
);

CREATE INDEX IF NOT EXISTS idx_maritime_boundaries_geom 
ON maritime_boundaries USING GIST (geom);

-- 3. Maritime Policy & Safety Rules Vector Storage (RAG for Evidence Synthesis)
CREATE TABLE IF NOT EXISTS advisory_embeddings (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    category VARCHAR(100) DEFAULT 'POLICY', -- 'SAFETY_RULE', 'EEZ_REGULATION'
    content TEXT NOT NULL,
    embedding VECTOR(1536)               -- Compatible with Mistral/OpenAI 1536-dim embeddings
);

-- Cosine distance index for sub-millisecond semantic search
CREATE INDEX IF NOT EXISTS idx_advisory_embeddings_cosine 
ON advisory_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);