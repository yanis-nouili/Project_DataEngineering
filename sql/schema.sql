-- Tables principales

CREATE TABLE IF NOT EXISTS standings (
  id SERIAL PRIMARY KEY,
  season VARCHAR(20),
  rank INT,
  team VARCHAR(100),
  played INT,
  wins INT,
  draws INT,
  losses INT,
  goals_for INT,
  goals_against INT,
  goal_diff INT,
  points INT,
  logo_url TEXT,
  scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (season, team)
);

CREATE TABLE IF NOT EXISTS scorers (
  id SERIAL PRIMARY KEY,
  season VARCHAR(20),
  rank INT,
  player_name VARCHAR(120),
  team VARCHAR(120),
  goals INT,
  penalties INT,
  team_logo_url TEXT,
  photo_url TEXT,
  logo_url TEXT,
  scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (season, player_name)
);

CREATE TABLE IF NOT EXISTS assists (
  id SERIAL PRIMARY KEY,
  season VARCHAR(20) NOT NULL,
  rank INT,
  player_name VARCHAR(120) NOT NULL,
  team VARCHAR(120),
  assists INT,
  team_logo_url TEXT,
  photo_url TEXT,
  logo_url TEXT,
  scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (season, player_name)
);

-- Palmarès

CREATE TABLE IF NOT EXISTS palmares_clubs (
  id SERIAL PRIMARY KEY,
  team VARCHAR(120) NOT NULL UNIQUE,
  titles INT NOT NULL DEFAULT 0,
  logo_url TEXT,
  scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS palmares_history (
  id SERIAL PRIMARY KEY,
  season VARCHAR(20) NOT NULL UNIQUE,
  winner VARCHAR(120),
  runner_up VARCHAR(120),
  winner_logo TEXT,
  runner_up_logo TEXT,
  scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
