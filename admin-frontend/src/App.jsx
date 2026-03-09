import React, { useState, useEffect } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

function Login({ onLogin }) {
  const [login, setLogin] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ login, password })
      });
      if (!res.ok) {
        throw new Error("Неверный логин или пароль");
      }
      const data = await res.json();
      onLogin(data.token);
    } catch (err) {
      setError(err.message || "Ошибка входа");
    }
  };

  return (
    <div style={{ maxWidth: 320, margin: "80px auto", padding: 24, border: "1px solid #ddd", borderRadius: 8 }}>
      <h2>Вход в админку</h2>
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <label>
          Логин
          <input value={login} onChange={(e) => setLogin(e.target.value)} />
        </label>
        <label>
          Пароль
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        {error && <div style={{ color: "red" }}>{error}</div>}
        <button type="submit">Войти</button>
      </form>
    </div>
  );
}

function TableList({ token, onSelect }) {
  const [tables, setTables] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/tables`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (!res.ok) throw new Error("Не удалось загрузить список таблиц");
        const data = await res.json();
        setTables(data);
      } catch (err) {
        setError(err.message);
      }
    })();
  }, [token]);

  return (
    <div style={{ padding: 16, borderRight: "1px solid #ddd", minWidth: 200 }}>
      <h3>Таблицы</h3>
      {error && <div style={{ color: "red" }}>{error}</div>}
      <ul style={{ listStyle: "none", padding: 0 }}>
        {tables.map((t) => (
          <li key={t}>
            <button onClick={() => onSelect(t)} style={{ width: "100%", textAlign: "left", marginBottom: 4 }}>
              {t}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function TableView({ token, table }) {
  const [rows, setRows] = useState([]);
  const [edited, setEdited] = useState({});
  const [status, setStatus] = useState("");

  useEffect(() => {
    if (!table) return;
    (async () => {
      setStatus("Загрузка...");
      try {
        const res = await fetch(`${API_BASE}/api/table/${table}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (!res.ok) throw new Error("Не удалось загрузить данные");
        const data = await res.json();
        setRows(data.rows || []);
        setEdited({});
        setStatus("");
      } catch (err) {
        setStatus(err.message);
      }
    })();
  }, [token, table]);

  const handleChange = (id, field, value) => {
    setEdited((prev) => ({
      ...prev,
      [id]: { ...(prev[id] || {}), [field]: value }
    }));
  };

  const handleSave = async (id) => {
    const changes = edited[id];
    if (!changes) return;
    setStatus("Сохранение...");
    try {
      const res = await fetch(`${API_BASE}/api/table/${table}/${id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ values: changes })
      });
      if (!res.ok) throw new Error("Ошибка сохранения");
      setStatus("Сохранено");
      setTimeout(() => setStatus(""), 1000);
    } catch (err) {
      setStatus(err.message);
    }
  };

  if (!table) return <div style={{ padding: 16 }}>Выберите таблицу слева.</div>;
  if (!rows.length) return <div style={{ padding: 16 }}>Нет данных.</div>;

  const columns = Object.keys(rows[0]);

  return (
    <div style={{ padding: 16, flex: 1, overflow: "auto" }}>
      <h3>{table}</h3>
      {status && <div style={{ marginBottom: 8 }}>{status}</div>}
      <table border="1" cellPadding="4" cellSpacing="0">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c}>{c}</th>
            ))}
            <th>Действия</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              {columns.map((col) => (
                <td key={col}>
                  <input
                    style={{ minWidth: 80 }}
                    value={
                      edited[row.id]?.[col] !== undefined
                        ? edited[row.id][col]
                        : row[col] === null || row[col] === undefined
                        ? ""
                        : String(row[col])
                    }
                    onChange={(e) => handleChange(row.id, col, e.target.value)}
                    disabled={col === "id"}
                  />
                </td>
              ))}
              <td>
                <button onClick={() => handleSave(row.id)}>Сохранить</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function App() {
  const [token, setToken] = useState(null);
  const [table, setTable] = useState(null);

  if (!token) {
    return <Login onLogin={setToken} />;
  }

  return (
    <div style={{ display: "flex", height: "100vh", fontFamily: "sans-serif" }}>
      <TableList token={token} onSelect={setTable} />
      <TableView token={token} table={table} />
    </div>
  );
}

