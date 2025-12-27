import { useState, useEffect } from "react";
import { getPlayers, Player } from "../api";
import { useDebounce } from "../hooks/useApi";

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
  
  const debouncedQuery = useDebounce(query, 250);

  useEffect(() => {
    async function fetchPlayers() {
      setLoading(true);
      try {
        const res = await getPlayers(debouncedQuery, 500);
        setPlayers(res.players);
      } catch (err) {
        console.error("Failed to fetch players:", err);
      } finally {
        setLoading(false);
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
        />
      </div>

      {loading ? (
        <div className="loading">
          <div className="spinner" />
        </div>
      ) : (
        <div className="player-list">
          {players.map((player) => (
            <div
              key={player.name}
              className={`player-item ${
                selectedPlayer?.name === player.name ? "player-item--selected" : ""
              }`}
              onClick={() => onSelect(player)}
            >
              <span className="player-item__name">{player.name}</span>
              <div className="player-item__stats">
                <span>{player.total_shots.toLocaleString()} shots</span>
                <span>{(player.fg_pct * 100).toFixed(1)}%</span>
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
