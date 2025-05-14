CREATE TABLE users (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    balance INTEGER DEFAULT 200,
    slots INTEGER DEFAULT 3
);

CREATE TABLE user_farms (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    farm_type TEXT,
    level INTEGER DEFAULT 1,
    crit_level INTEGER DEFAULT 1,
    next_collect TIMESTAMP,
    active BOOLEAN DEFAULT TRUE,
    slot INTEGER
);

ALTER TABLE user_farms
ADD COLUMN last_paid TIMESTAMP;
