import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../lib/api";

type OrderSummary = {
  id: string;
  status: string;
  currency: string;
  total_amount: number;
  created_at: string;
};

type OrderListResponse = {
  items: OrderSummary[];
  next_cursor: string | null;
};

const OrdersPage = () => {
  const [orders, setOrders] = useState<OrderSummary[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadOrders = async (cursor?: string | null, statusFilter?: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<OrderListResponse>("/orders", {
        params: {
          limit: 20,
          cursor: cursor ?? undefined,
          status: statusFilter || undefined,
        },
      });
      const data = res.data;
      if (cursor) {
        setOrders((prev) => [...prev, ...data.items]);
      } else {
        setOrders(data.items);
      }
      setNextCursor(data.next_cursor);
    } catch (err) {
      setError("Failed to load orders");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOrders(null, status);
  }, [status]);

  return (
    <main className="page">
      <div className="card">
        <h1>Orders</h1>
        <div className="toolbar">
          <label>
            Status
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">All</option>
              <option value="created">created</option>
              <option value="paid">paid</option>
              <option value="canceled">canceled</option>
            </select>
          </label>
        </div>
        {error ? <p className="error">{error}</p> : null}
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Status</th>
              <th>Total</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((order) => (
              <tr key={order.id}>
                <td>
                  <Link to={`/orders/${order.id}`}>{order.id}</Link>
                </td>
                <td>{order.status}</td>
                <td>
                  {order.total_amount} {order.currency}
                </td>
                <td>{order.created_at}</td>
              </tr>
            ))}
            {orders.length === 0 && !loading ? (
              <tr>
                <td colSpan={4}>No orders</td>
              </tr>
            ) : null}
          </tbody>
        </table>
        <div className="actions">
          <button
            type="button"
            disabled={!nextCursor || loading}
            onClick={() => loadOrders(nextCursor, status)}
          >
            {loading ? "Loading..." : "Load more"}
          </button>
        </div>
      </div>
    </main>
  );
};

export default OrdersPage;
