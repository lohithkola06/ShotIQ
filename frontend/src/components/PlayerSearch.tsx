import { useState, useEffect } from "react";
import { getPlayers, Player } from "../api";
import { useDebounce } from "../hooks/useApi";
import { useRef } from "react";

interface PlayerSearchProps {
  onSelect: (player: Player) => void;
  selectedPlayer?: Player | null;
  placeholder?: string;
}

export function PlayerSearch({
  onSelect,
  selectedPlayer,
  placeholder = "Search players...",
}: PlayerSearchProps) {
  const [query, setQuery] = useState("");
  const [players, setPlayers] = useState<Player[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const activeRequest = useRef(0);
  
  const debouncedQuery = useDebounce(query, 200);

  useEffect(() => {
    async function fetchPlayers() {
      setLoading(true);
      setError(null);
      const requestId = ++activeRequest.current;
      try {
        const res = await getPlayers(debouncedQuery, 100);
        // Ignore stale responses that return after a newer query
        if (requestId === activeRequest.current) {
          setPlayers(res.players);
        }
      } catch (err) {
        console.error("Failed to fetch players:", err);
        setError("Unable to load players.");
        setPlayers([]);
      } finally {
        if (requestId === activeRequest.current) {
          setLoading(false);
        }
      }
    }
    fetchPlayers();
  }, [debouncedQuery]);

  return (
    <div>
      <div className="search">
        <span className="search__icon">⌕</span>
        <input
          type="text"
          className="search__input"
          placeholder={placeholder}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoComplete="off"
        />
      </div>

      {loading ? (
        <div className="loading">
          <div className="spinner" />
        </div>
      ) : (
        <div className="player-list">
          {error && (
            <div className="empty-state">
              <p>{error}</p>
            </div>
          )}
          {players.map((player) => (
            <div
              key={player.name}
              className={`player-item ${
                selectedPlayer?.name === player.name ? "player-item--selected" : ""
              }`}
              onClick={() => onSelect(player)}
            >
              <div className="player-item__info">
                <div className="player-item__name">{player.name}</div>
                <div className="player-item__meta">
                  <span className="pill pill--shots">{player.total_shots.toLocaleString()} shots</span>
                  <span className="pill pill--fg">{(player.fg_pct * 100).toFixed(1)}%</span>
                </div>
              </div>
            </div>
          ))}
          {players.length === 0 && (
            <div className="empty-state">
              <p>No players found</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
