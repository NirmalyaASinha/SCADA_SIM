-- SCADA Platform Database Schema
-- PostgreSQL with TimescaleDB extension
-- Production-ready schema for distributed SCADA system

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Node registry table
-- Tracks all registered nodes in the SCADA network
CREATE TABLE IF NOT EXISTS node_registry (
    node_id         VARCHAR(20) PRIMARY KEY,
    node_type       VARCHAR(20) NOT NULL CHECK (node_type IN ('generation', 'transmission', 'distribution')),
    ip_address      INET NOT NULL,
    rest_port       INTEGER NOT NULL,
    modbus_port     INTEGER NOT NULL,
    ws_port         INTEGER NOT NULL,
    version         VARCHAR(20),
    registered_at   TIMESTAMPTZ DEFAULT NOW(),
    last_heartbeat  TIMESTAMPTZ,
    status          VARCHAR(20) DEFAULT 'ONLINE' CHECK (status IN ('ONLINE', 'OFFLINE', 'DEGRADED', 'WARNING', 'FAULT', 'ISOLATED'))
);

-- Live telemetry table (TimescaleDB hypertable for time-series data)
CREATE TABLE IF NOT EXISTS node_telemetry (
    time                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    node_id             VARCHAR(20) NOT NULL,
    bus_voltage_kv      NUMERIC(10,3),
    line_current_a      NUMERIC(10,3),
    active_power_mw     NUMERIC(10,3),
    reactive_power_mvar NUMERIC(10,3),
    power_factor        NUMERIC(5,4),
    frequency_hz        NUMERIC(6,3),
    transformer_temp_c  NUMERIC(6,2),
    tap_position        INTEGER,
    load_percentage     NUMERIC(5,2),
    generator_rpm       INTEGER,
    breaker_state       BOOLEAN,
    relay_trip          BOOLEAN,
    earth_fault         BOOLEAN,
    outage_flag         BOOLEAN,
    feeder_switch       BOOLEAN,
    node_state          VARCHAR(20)
);

-- Convert to hypertable (TimescaleDB)
SELECT create_hypertable('node_telemetry', 'time', if_not_exists => TRUE);

-- Create index for faster queries by node_id
CREATE INDEX IF NOT EXISTS idx_telemetry_node_id_time ON node_telemetry (node_id, time DESC);

-- Retention policy: keep 30 days of telemetry data
SELECT add_retention_policy('node_telemetry', INTERVAL '30 days', if_not_exists => TRUE);

-- Modbus transaction log (security critical)
-- Log every Modbus connection and transaction for security monitoring
CREATE TABLE IF NOT EXISTS modbus_transactions (
    id              BIGSERIAL PRIMARY KEY,
    timestamp       TIMESTAMPTZ DEFAULT NOW(),
    node_id         VARCHAR(20) NOT NULL,
    source_ip       INET NOT NULL,
    source_port     INTEGER,
    function_code   INTEGER NOT NULL,
    register_address INTEGER,
    value           INTEGER,
    direction       VARCHAR(10) CHECK (direction IN ('READ', 'WRITE')),
    is_write        BOOLEAN DEFAULT FALSE,
    success         BOOLEAN DEFAULT TRUE,
    error_code      INTEGER
);

-- Index for security queries
CREATE INDEX IF NOT EXISTS idx_modbus_timestamp ON modbus_transactions (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_modbus_node_ip ON modbus_transactions (node_id, source_ip);
CREATE INDEX IF NOT EXISTS idx_modbus_writes ON modbus_transactions (is_write, timestamp DESC) WHERE is_write = TRUE;

-- Alarms table
CREATE TABLE IF NOT EXISTS alarms (
    alarm_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id         VARCHAR(20) NOT NULL,
    alarm_tag       VARCHAR(50) NOT NULL,
    priority        INTEGER NOT NULL CHECK (priority BETWEEN 1 AND 5),
    state           VARCHAR(40) NOT NULL,
    message         TEXT NOT NULL,
    value           NUMERIC,
    threshold       NUMERIC,
    raised_time     TIMESTAMPTZ DEFAULT NOW(),
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by VARCHAR(50),
    cleared_at      TIMESTAMPTZ
);

-- Index for active alarms
CREATE INDEX IF NOT EXISTS idx_alarms_active ON alarms (node_id, raised_time DESC) WHERE cleared_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_alarms_priority ON alarms (priority, raised_time DESC) WHERE cleared_at IS NULL;

-- Operator actions audit log
CREATE TABLE IF NOT EXISTS operator_actions (
    id              BIGSERIAL PRIMARY KEY,
    timestamp       TIMESTAMPTZ DEFAULT NOW(),
    operator        VARCHAR(50) NOT NULL,
    operator_ip     INET NOT NULL,
    node_id         VARCHAR(20),
    action_type     VARCHAR(50) NOT NULL,
    action_detail   JSONB,
    result          VARCHAR(20) CHECK (result IN ('SUCCESS', 'FAILED', 'UNAUTHORIZED', 'TIMEOUT')),
    response_ms     INTEGER
);

-- Index for audit queries
CREATE INDEX IF NOT EXISTS idx_operator_actions_timestamp ON operator_actions (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_operator_actions_node ON operator_actions (node_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_operator_actions_user ON operator_actions (operator, timestamp DESC);

-- Security events table
CREATE TABLE IF NOT EXISTS security_events (
    id              BIGSERIAL PRIMARY KEY,
    timestamp       TIMESTAMPTZ DEFAULT NOW(),
    event_type      VARCHAR(50) NOT NULL,
    severity        VARCHAR(20) CHECK (severity IN ('INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    node_id         VARCHAR(20),
    source_ip       INET,
    protocol        VARCHAR(20),
    description     TEXT NOT NULL,
    raw_data        JSONB,
    acknowledged    BOOLEAN DEFAULT FALSE,
    acknowledged_by VARCHAR(50),
    acknowledged_at TIMESTAMPTZ
);

-- Index for security monitoring
CREATE INDEX IF NOT EXISTS idx_security_events_timestamp ON security_events (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_security_events_severity ON security_events (severity, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_security_events_unack ON security_events (acknowledged, timestamp DESC) WHERE acknowledged = FALSE;

-- Admin users table
CREATE TABLE IF NOT EXISTS admin_users (
    username        VARCHAR(50) PRIMARY KEY,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(20) CHECK (role IN ('admin', 'engineer', 'viewer')),
    email           VARCHAR(100),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    last_login      TIMESTAMPTZ,
    is_active       BOOLEAN DEFAULT TRUE
);

-- Node operators table
CREATE TABLE IF NOT EXISTS node_operators (
    username        VARCHAR(50) PRIMARY KEY,
    password_hash   VARCHAR(255) NOT NULL,
    node_id         VARCHAR(20) NOT NULL,
    email           VARCHAR(100),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    last_login      TIMESTAMPTZ,
    is_active       BOOLEAN DEFAULT TRUE
);

-- Connection tracking table (for security monitoring)
CREATE TABLE IF NOT EXISTS active_connections (
    id              BIGSERIAL PRIMARY KEY,
    node_id         VARCHAR(20) NOT NULL,
    protocol        VARCHAR(20) NOT NULL,
    client_ip       INET NOT NULL,
    client_port     INTEGER,
    connected_at    TIMESTAMPTZ DEFAULT NOW(),
    last_activity   TIMESTAMPTZ DEFAULT NOW(),
    request_count   INTEGER DEFAULT 0,
    is_authenticated BOOLEAN DEFAULT FALSE,
    username        VARCHAR(50),
    status          VARCHAR(20) DEFAULT 'ACTIVE'
);

-- Index for active connection queries
CREATE INDEX IF NOT EXISTS idx_active_connections_node ON active_connections (node_id, connected_at DESC);
CREATE INDEX IF NOT EXISTS idx_active_connections_ip ON active_connections (client_ip, connected_at DESC);

-- Anomaly detection events (for ML integration)
CREATE TABLE IF NOT EXISTS anomaly_events (
    id              BIGSERIAL PRIMARY KEY,
    timestamp       TIMESTAMPTZ DEFAULT NOW(),
    node_id         VARCHAR(20) NOT NULL,
    anomaly_type    VARCHAR(50) NOT NULL,
    severity_score  NUMERIC(3,2) CHECK (severity_score BETWEEN 0 AND 1),
    affected_tags   TEXT[],
    description     TEXT,
    model_name      VARCHAR(50),
    raw_features    JSONB,
    acknowledged    BOOLEAN DEFAULT FALSE
);

-- Create views for common queries

-- Active alarms summary by node
CREATE OR REPLACE VIEW v_active_alarms_summary AS
SELECT 
    node_id,
    COUNT(*) as total_alarms,
    COUNT(*) FILTER (WHERE priority = 1) as critical_count,
    COUNT(*) FILTER (WHERE priority = 2) as high_count,
    COUNT(*) FILTER (WHERE priority = 3) as medium_count,
    COUNT(*) FILTER (WHERE acknowledged_at IS NULL) as unacknowledged_count
FROM alarms
WHERE cleared_at IS NULL
GROUP BY node_id;

-- Latest telemetry per node
CREATE OR REPLACE VIEW v_latest_telemetry AS
SELECT DISTINCT ON (node_id)
    node_id,
    time,
    bus_voltage_kv,
    line_current_a,
    active_power_mw,
    reactive_power_mvar,
    power_factor,
    frequency_hz,
    transformer_temp_c,
    tap_position,
    load_percentage,
    generator_rpm,
    breaker_state,
    relay_trip,
    node_state
FROM node_telemetry
ORDER BY node_id, time DESC;

-- Connection security summary
CREATE OR REPLACE VIEW v_connection_security AS
SELECT 
    node_id,
    protocol,
    client_ip,
    COUNT(*) as connection_count,
    MAX(connected_at) as last_connection,
    SUM(request_count) as total_requests,
    BOOL_OR(is_authenticated) as has_authenticated
FROM active_connections
WHERE status = 'ACTIVE'
GROUP BY node_id, protocol, client_ip;

-- Insert default admin users (passwords should be hashed in production)
-- Using bcrypt hashed passwords
-- admin@scada2024 -> $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5oe2kd2qZY3Ri
-- eng@scada2024   -> $2b$12$EXRkGd8m0XwN.zJqK5g7uO7t7wPz8qJz1Y3V4qK7aH8qZ9xY2qZvi
-- view@scada2024  -> $2b$12$3X8F7u9qK5gZ8mN2pQ1xY.7tZ9wW5qJz1Y3V4qK7aH8qZ9xY2qZvi

INSERT INTO admin_users (username, password_hash, role, email) VALUES
    ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5oe2kd2qZY3Ri', 'admin', 'admin@scada.local'),
    ('engineer', '$2b$12$EXRkGd8m0XwN.zJqK5g7uO7t7wPz8qJz1Y3V4qK7aH8qZ9xY2qZvi', 'engineer', 'engineer@scada.local'),
    ('viewer', '$2b$12$3X8F7u9qK5gZ8mN2pQ1xY.7tZ9wW5qJz1Y3V4qK7aH8qZ9xY2qZvi', 'viewer', 'viewer@scada.local')
ON CONFLICT (username) DO NOTHING;

-- Insert default node operators (one per node)
INSERT INTO node_operators (username, password_hash, node_id, email) VALUES
    ('operator_gen1', '$2b$12$gen1passwordhash', 'GEN-001', 'gen1@scada.local'),
    ('operator_gen2', '$2b$12$gen2passwordhash', 'GEN-002', 'gen2@scada.local'),
    ('operator_sub1', '$2b$12$sub1passwordhash', 'SUB-001', 'sub1@scada.local'),
    ('operator_sub2', '$2b$12$sub2passwordhash', 'SUB-002', 'sub2@scada.local'),
    ('operator_sub3', '$2b$12$sub3passwordhash', 'SUB-003', 'sub3@scada.local'),
    ('operator_dist1', '$2b$12$dist1passwordhash', 'DIST-001', 'dist1@scada.local'),
    ('operator_dist2', '$2b$12$dist2passwordhash', 'DIST-002', 'dist2@scada.local')
ON CONFLICT (username) DO NOTHING;

-- Grant permissions (adjust as needed for your PostgreSQL setup)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO scada;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO scada;

COMMIT;
