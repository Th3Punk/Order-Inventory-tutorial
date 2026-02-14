import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { api } from "../lib/api";

type OrderItem = {
  sku: string;
  qty: number;
  unit_price: number;
  line_total: number;
};

type Order = {
  id: string;
  status: string;
  currency: string;
  total_amount: number;
  items: OrderItem[];
  created_at: string;
};

const OrderDetailsPage = () => {
  const { id } = useParams();
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);

  const loadOrder = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<Order>(`/orders/${id}`);
      setOrder(res.data);
    } catch {
      setError("Failed to load order");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOrder();
  }, [id]);

  const updateStatus = async (status: string) => {
    if (!id) return;
    setUpdating(true);
    try {
      await api.patch(`/orders/${id}/status`, { status });
      await loadOrder();
    } catch {
      setError("Failed to update status");
    } finally {
      setUpdating(false);
    }
  };

  return (
    <main className="page">
      <div className="card">
        <h1>Order details</h1>
        {loading ? <p>Loading...</p> : null}
        {error ? <p className="error">{error}</p> : null}
        {order ? (
          <>
            <div className="details-grid">
              <div>
                <strong>ID</strong>
                <div>{order.id}</div>
              </div>
              <div>
                <strong>Status</strong>
                <div>{order.status}</div>
              </div>
              <div>
                <strong>Total</strong>
                <div>
                  {order.total_amount} {order.currency}
                </div>
              </div>
              <div>
                <strong>Created</strong>
                <div>{order.created_at}</div>
              </div>
            </div>
            <h2>Items</h2>
            <table className="table">
              <thead>
                <tr>
                  <th>SKU</th>
                  <th>Qty</th>
                  <th>Unit price</th>
                  <th>Line total</th>
                </tr>
              </thead>
              <tbody>
                {order.items.map((item, index) => (
                  <tr key={`${item.sku}-${index}`}>
                    <td>{item.sku}</td>
                    <td>{item.qty}</td>
                    <td>{item.unit_price}</td>
                    <td>{item.line_total}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="actions">
              {order.status === "created" ? (
                <>
                  <button
                    type="button"
                    disabled={updating}
                    onClick={() => updateStatus("paid")}
                  >
                    Mark paid
                  </button>
                  <button
                    type="button"
                    disabled={updating}
                    onClick={() => updateStatus("canceled")}
                  >
                    Cancel
                  </button>
                </>
              ) : null}
            </div>
          </>
        ) : null}
      </div>
    </main>
  );
};

export default OrderDetailsPage;
