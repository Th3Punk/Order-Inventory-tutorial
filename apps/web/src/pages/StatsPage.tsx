import { useEffect, useState } from "react";

import { api } from "../lib/api";

type SkuStat = {
  sku: string;
  window_start: string;
  window_end: string;
  total_qty: number;
};

const StatsPage = () => {
  const [items, setItems] = useState<SkuStat[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fromTs, setFromTs] = useState("");
  const [toTs, setToTs] = useState("");

  const loadStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = { limit: "50" };
      if (fromTs) {
        params.from_ts = new Date(fromTs).toISOString();
      }
      if (toTs) {
        params.to_ts = new Date(toTs).toISOString();
      }
      const res = await api.get<{ items: SkuStat[] }>("/stats/sku", {
        params,
      });
      setItems(res.data.items);
    } catch {
      setError("Failed to load stats");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
  }, []);

  return (
    <main className="page">
      <div className="card">
        <h1>Stats</h1>
        <div className="filters">
          <label>
            From
            <input
              type="datetime-local"
              value={fromTs}
              onChange={(e) => setFromTs(e.target.value)}
            />
          </label>
          <label>
            To
            <input
              type="datetime-local"
              value={toTs}
              onChange={(e) => setToTs(e.target.value)}
            />
          </label>
          <button type="button" onClick={loadStats} disabled={loading}>
            {loading ? "Loading..." : "Apply"}
          </button>
        </div>
        {loading ? <p>Loading...</p> : null}
        {error ? <p className="error">{error}</p> : null}
        <table className="table">
          <thead>
            <tr>
              <th>SKU</th>
              <th>Window start</th>
              <th>Window end</th>
              <th>Total qty</th>
            </tr>
          </thead>
          <tbody>
            {items.map((row, i) => (
              <tr key={`${row.sku}-${row.window_start}-${i}`}>
                <td>{row.sku}</td>
                <td>{row.window_start}</td>
                <td>{row.window_end}</td>
                <td>{row.total_qty}</td>
              </tr>
            ))}
            {items.length === 0 && !loading ? (
              <tr>
                <td colSpan={4}>No stats</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </main>
  );
};

export default StatsPage;
