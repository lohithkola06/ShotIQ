-- Run this in Supabase SQL Editor after creating and indexing the shots table.

-- Optional: give longer time for heavy queries
ALTER DATABASE postgres SET statement_timeout = '30s';

-- Precompute player aggregates for faster /api/players
CREATE MATERIALIZED VIEW IF NOT EXISTS player_shot_agg AS
SELECT
  player_name AS name,
  COUNT(*)::BIGINT AS total_shots,
  ROUND(AVG(shot_made_flag)::NUMERIC, 3) AS fg_pct
FROM shots
GROUP BY player_name;

CREATE UNIQUE INDEX IF NOT EXISTS idx_player_shot_agg_name ON player_shot_agg(name);
CREATE INDEX IF NOT EXISTS idx_player_shot_agg_total ON player_shot_agg(total_shots DESC);

-- Function to get players with stats (reads the materialized view)
CREATE OR REPLACE FUNCTION get_players_with_stats(
  search_term TEXT DEFAULT '',
  min_shot_count INT DEFAULT 100,
  result_limit INT DEFAULT 100
)
RETURNS TABLE (
  name TEXT,
  total_shots BIGINT,
  fg_pct NUMERIC
) AS $$
  SET LOCAL statement_timeout = '30s';
BEGIN
  RETURN QUERY
  SELECT 
    p.name,
    p.total_shots,
    p.fg_pct
  FROM player_shot_agg p
  WHERE 
    (search_term = '' OR p.name ILIKE '%' || search_term || '%')
    AND p.total_shots >= min_shot_count
  ORDER BY p.total_shots DESC
  LIMIT result_limit;
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to get available years
CREATE OR REPLACE FUNCTION get_available_years()
RETURNS TABLE (year SMALLINT) AS $$
BEGIN
  RETURN QUERY
  SELECT DISTINCT s.year
  FROM shots s
  ORDER BY s.year;
END;
$$ LANGUAGE plpgsql;

-- Function to get player stats
CREATE OR REPLACE FUNCTION get_player_stats(
  p_player_name TEXT,
  p_years INT[] DEFAULT NULL
)
RETURNS JSON AS $$
DECLARE
  result JSON;
BEGIN
  WITH player_shots AS (
    SELECT *
    FROM shots
    WHERE player_name = p_player_name
    AND (p_years IS NULL OR year = ANY(p_years))
  ),
  basic_stats AS (
    SELECT 
      player_name,
      COUNT(*) as total_shots,
      SUM(shot_made_flag) as made_shots,
      ROUND(AVG(shot_made_flag)::NUMERIC, 3) as fg_pct,
      ROUND(AVG(shot_distance)::NUMERIC, 1) as avg_distance
    FROM player_shots
    GROUP BY player_name
  ),
  shot_types AS (
    SELECT 
      shot_type,
      COUNT(*) as attempts,
      SUM(shot_made_flag) as made,
      ROUND(AVG(shot_made_flag)::NUMERIC, 3) as fg_pct
    FROM player_shots
    GROUP BY shot_type
  ),
  seasons AS (
    SELECT 
      year,
      COUNT(*) as attempts,
      SUM(shot_made_flag) as made,
      ROUND(AVG(shot_made_flag)::NUMERIC, 3) as fg_pct
    FROM player_shots
    GROUP BY year
    ORDER BY year
  ),
  zones AS (
    SELECT 
      CASE 
        WHEN shot_distance <= 5 THEN 'Paint (0-5ft)'
        WHEN shot_distance <= 10 THEN 'Short (5-10ft)'
        WHEN shot_distance <= 15 THEN 'Mid (10-15ft)'
        WHEN shot_distance <= 22 THEN 'Long 2 (15-22ft)'
        ELSE '3PT (22+ft)'
      END as zone,
      COUNT(*) as attempts,
      SUM(shot_made_flag) as made,
      ROUND(AVG(shot_made_flag)::NUMERIC, 3) as fg_pct
    FROM player_shots
    GROUP BY 1
  ),
  actions AS (
    SELECT 
      action_type,
      COUNT(*) as attempts,
      SUM(shot_made_flag) as made,
      ROUND(AVG(shot_made_flag)::NUMERIC, 3) as fg_pct
    FROM player_shots
    GROUP BY action_type
    ORDER BY COUNT(*) DESC
    LIMIT 10
  )
  SELECT json_build_object(
    'player_name', (SELECT player_name FROM basic_stats),
    'total_shots', (SELECT total_shots FROM basic_stats),
    'made_shots', (SELECT made_shots FROM basic_stats),
    'fg_pct', (SELECT fg_pct FROM basic_stats),
    'avg_distance', (SELECT avg_distance FROM basic_stats),
    'shot_types', (SELECT json_agg(row_to_json(shot_types)) FROM shot_types),
    'seasons', (SELECT json_agg(row_to_json(seasons)) FROM seasons),
    'zones', (SELECT json_agg(row_to_json(zones)) FROM zones),
    'actions', (SELECT json_agg(row_to_json(actions)) FROM actions)
  ) INTO result;
  
  RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Refresh when new data is loaded
REFRESH MATERIALIZED VIEW CONCURRENTLY player_shot_agg;
