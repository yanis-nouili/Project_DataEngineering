-- Table du classement Ligue 1
CREATE TABLE IF NOT EXISTS standings (
    id SERIAL PRIMARY KEY,
    season VARCHAR(20),
    rank INTEGER,
    team VARCHAR(100),
    played INTEGER,
    wins INTEGER,
    draws INTEGER,
    losses INTEGER,
    goals_for INTEGER,
    goals_against INTEGER,
    goal_diff INTEGER,
    points INTEGER,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (season, team)
);

-- Table des matchs (calendrier)
CREATE TABLE IF NOT EXISTS matches (
    id SERIAL PRIMARY KEY,
    season VARCHAR(20),
    matchday INTEGER,
    match_date DATE,
    home_team VARCHAR(100),
    away_team VARCHAR(100),
    home_score INTEGER,
    away_score INTEGER,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (season, matchday, home_team, away_team)
);

-- Table des buteurs
CREATE TABLE IF NOT EXISTS scorers (
    id SERIAL PRIMARY KEY,
    season VARCHAR(20),
    rank INTEGER,
    player_name VARCHAR(100),
    team VARCHAR(100),
    goals INTEGER,
    penalties INTEGER,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (season, player_name)
);
