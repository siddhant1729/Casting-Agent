import { useCallback, useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { Sidebar } from "./components/Sidebar";
import { Topbar } from "./components/Topbar";
import { Casting } from "./pages/Casting";
import { Compare } from "./pages/Compare";
import { fetchMeta } from "./lib/api";
import type { Meta } from "./lib/types";

export default function App() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [error, setError] = useState<string | null>(null);

  // One failed load must not be terminal. The API is often still booting when
  // the page first mounts — uvicorn's reloader takes a couple of seconds — and
  // an unrecoverable error screen for a two-second race sends people to restart
  // things that were never broken.
  const load = useCallback(() => {
    setError(null);
    fetchMeta()
      .then(setMeta)
      .catch(() =>
        setError(
          "Can't reach the API. It may still be starting — check it with: " +
            "curl localhost:8000/api/health",
        ),
      );
  }, []);

  useEffect(() => { load(); }, [load]);

  // Retry quietly while it is still coming up, rather than making the user
  // reload the page to find out.
  useEffect(() => {
    if (!error || meta) return;
    const timer = setTimeout(load, 2000);
    return () => clearTimeout(timer);
  }, [error, meta, load]);

  return (
    <div className="shell">
      <Sidebar />
      <div className="main">
        <Topbar />

        <div className="panel">
          <div className="eyebrow">
            <span className="dot" aria-hidden="true" />
            Casting Agent · prototype
          </div>

          <div className="hero">
            <div>
              <h1>
                Cast with <em>precision</em> for your campaign.
              </h1>
              <p>
                Semantic matching across distinct actor-looks, delivery profiles and
                staging environments — moving beyond blunt keyword search.
              </p>
            </div>

            <nav className="tabs" aria-label="Casting views">
              <NavLink to="/" end className={({ isActive }) => `tab${isActive ? " active" : ""}`}>
                Brief &amp; ranked looks
              </NavLink>
              <NavLink to="/compare" className={({ isActive }) => `tab${isActive ? " active" : ""}`}>
                Live comparison: keyword vs semantic
                <span className="badge">CORE DEMO</span>
              </NavLink>
            </nav>
          </div>

          {error && (
            <p className="error" role="alert" style={{ marginTop: 24 }}>
              {error}{" "}
              <button className="btn ghost" style={{ marginLeft: 8 }} onClick={load}>
                Retry now
              </button>
            </p>
          )}
          {!meta && !error && <p className="muted" style={{ marginTop: 24 }}>loading…</p>}

          {meta && (
            <Routes>
              <Route path="/" element={<Casting meta={meta} />} />
              <Route path="/compare" element={<Compare meta={meta} />} />
            </Routes>
          )}
        </div>
      </div>
    </div>
  );
}
