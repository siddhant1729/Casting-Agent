import type { ReactElement } from "react";
import { NavLink } from "react-router-dom";

// The product's own sidebar, with Casting sitting directly below Actors —
// which is the argument the prototype is making about where this belongs.
//
// Every other item is inert on purpose: dimmed, unfocusable, no hover, and
// announced as disabled. They mark the surrounding product so the placement
// reads correctly. Rendering them as links that go nowhere would be worse than
// not rendering them — a nav item that looks live and does nothing is a bug
// report waiting to happen.

interface Item {
  label: string;
  sub?: string;
  icon: ReactElement;
}

const stroke = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.6,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

const icon = (d: string) => (
  <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
    <path d={d} {...stroke} />
  </svg>
);

const PRIMARY: Item[] = [
  { label: "Home", icon: icon("M3 10.5 12 3l9 7.5M5.5 9.5V20h13V9.5") },
  { label: "Projects", icon: icon("M3 7.5h6l2 2.5h10V19H3z") },
  { label: "Renders", icon: icon("M4 20V9m5 11V4m5 16v-7m5 7V7") },
  { label: "Library", icon: icon("M12 6.5 5 4v14l7 2.5L19 18V4z M12 6.5v14") },
];

const TOOLS: Item[] = [
  { label: "URL → Ad", sub: "Link → ad video", icon: icon("M10 13a4 4 0 0 0 6 .5l2-2a4 4 0 0 0-5.7-5.7l-1 1M14 11a4 4 0 0 0-6-.5l-2 2A4 4 0 0 0 11.7 18l1-1") },
  { label: "Marketing Studio", sub: "Describe it, we make it", icon: icon("M4 19h16M6 19V9m4 10V5m4 14v-6m4 6V8") },
  { label: "Talking Actors", sub: "Actor speaks your script", icon: icon("M12 15a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v6a3 3 0 0 0 3 3zM6 12a6 6 0 0 0 12 0M12 18v3") },
  { label: "Creative Studio", sub: "Pick a model, generate", icon: icon("M6 3h9l3 3v15H6zM15 3v4h4") },
];

function Inert({ item }: { item: Item }) {
  return (
    <span className="nav-item inert" aria-disabled="true">
      {item.icon}
      <span>
        {item.label}
        {item.sub && <span className="sub">{item.sub}</span>}
      </span>
    </span>
  );
}

export function Sidebar() {
  return (
    <nav className="sidebar" aria-label="Main">
      <div className="wordmark">
        HEXCODED <span className="dot" />
      </div>

      <div className="nav">
        {PRIMARY.map((item) => (
          <Inert key={item.label} item={item} />
        ))}

        {/* Actors is the surface this replaces; Casting sits immediately under
            it. Actors stays inert — the comparison lives inside /compare. */}
        <Inert item={{ label: "Actors", icon: icon("M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4.5 20a7.5 7.5 0 0 1 15 0") }} />

        <NavLink
          to="/"
          end
          className={({ isActive }) => `nav-item live${isActive ? " active" : ""}`}
        >
          {icon("M4 6.5h11v11H4zM17 9.5l3-2v9l-3-2z")}
          <span>Casting</span>
        </NavLink>

        <div className="nav-label nav-tools">Tools</div>
        <div className="nav-tools">
          {TOOLS.map((item) => (
            <Inert key={item.label} item={item} />
          ))}
        </div>
      </div>

      <div className="sidebar-foot">
        <Inert item={{ label: "Settings", icon: icon("M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-2.7 1.1V21a2 2 0 1 1-4 0v-.1A1.6 1.6 0 0 0 7.5 19.4a1.6 1.6 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.6 1.6 0 0 0-1.1-2.7H1.7a2 2 0 1 1 0-4h.1A1.6 1.6 0 0 0 3.4 7.5") }} />
      </div>
    </nav>
  );
}
