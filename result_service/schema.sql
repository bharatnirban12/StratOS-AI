CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name VARCHAR(255),
    dob DATE,
    personal_api_key TEXT,
    usage_today INTEGER DEFAULT 0,
    last_usage_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS simulation (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    result JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
