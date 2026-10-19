CREATE SCHEMA IF NOT EXISTS etl_control;

CREATE TABLE IF NOT EXISTS etl_control.source_file_state (
    file_name VARCHAR(255) PRIMARY KEY,
    content_sha256 CHAR(64) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    rows_loaded BIGINT NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (file_size_bytes >= 0),
    CHECK (rows_loaded >= 0)
);