import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../lib/api";

type OrderItemForm = {
  sku: string;
  qty: number;
  unit_price: number;
};

const CreateOrderPage = () => {
  const navigate = useNavigate();
  const [currency, setCurrency] = useState("EUR");
  const [items, setItems] = useState<OrderItemForm[]>([
    { sku: "SKU-001", qty: 1, unit_price: 1000 },
  ]);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateItem = (index: number, patch: Partial<OrderItemForm>) => {
    setItems((prev) =>
      prev.map((item, i) => (i === index ? { ...item, ...patch } : item))
    );
  };

  const addItem = () => {
    setItems((prev) => [...prev, { sku: "SKU-NEW", qty: 1, unit_price: 1000 }]);
  };

  const removeItem = (index: number) => {
    setItems((prev) => prev.filter((_, i) => i !== index));
  };

  const createOrder = async () => {
    setCreating(true);
    setError(null);
    try {
      const idempotencyKey = crypto.randomUUID();
      await api.post(
        "/orders",
        { currency, items },
        { headers: { "Idempotency-Key": idempotencyKey } }
      );
      navigate("/orders");
    } catch {
      setError("Failed to create order");
    } finally {
      setCreating(false);
    }
  };

  return (
    <main className="page">
      <div className="card">
        <h1>Create order</h1>
        <div className="form-grid">
          <label>
            Currency
            <select value={currency} onChange={(e) => setCurrency(e.target.value)}>
              <option value="EUR">EUR</option>
              <option value="USD">USD</option>
              <option value="HUF">HUF</option>
            </select>
          </label>
        </div>
        <div className="items">
          {items.map((item, index) => (
            <div key={`${item.sku}-${index}`} className="item-row">
              <label>
                SKU
                <input
                  value={item.sku}
                  onChange={(e) => updateItem(index, { sku: e.target.value })}
                />
              </label>
              <label>
                Qty
                <input
                  type="number"
                  min={1}
                  value={item.qty}
                  onChange={(e) => updateItem(index, { qty: Number(e.target.value) })}
                />
              </label>
              <label>
                Unit price
                <input
                  type="number"
                  min={1}
                  value={item.unit_price}
                  onChange={(e) =>
                    updateItem(index, { unit_price: Number(e.target.value) })
                  }
                />
              </label>
              <button type="button" onClick={() => removeItem(index)}>
                Remove
              </button>
            </div>
          ))}
          <div className="item-actions">
            <button type="button" onClick={addItem}>
              Add item
            </button>
          </div>
        </div>
        {error ? <p className="error">{error}</p> : null}
        <button type="button" disabled={creating} onClick={createOrder}>
          {creating ? "Creating..." : "Create order"}
        </button>
      </div>
    </main>
  );
};

export default CreateOrderPage;
