// Deterministic abstract geometry from a per-actor seed sent by the API.
//
// The catalog is synthetic, so there is no real photograph to show — and a
// *generated* photoreal face is the one thing a placeholder must never be,
// because generated faces can resemble real people. The mark identifies a card
// consistently across renders without depicting anyone.

interface Props {
  seed: number;
  size?: number;
}

function rng(seed: number) {
  let state = seed % 2147483647;
  if (state <= 0) state += 2147483646;
  return () => (state = (state * 16807) % 2147483647) / 2147483647;
}

const PALETTES = [
  ["#d1fae5", "#6ee7b7", "#047857"],
  ["#dbeafe", "#93c5fd", "#1d4ed8"],
  ["#fef3c7", "#fcd34d", "#b45309"],
  ["#ede9fe", "#c4b5fd", "#6d28d9"],
  ["#fee2e2", "#fca5a5", "#b91c1c"],
];

export function Portrait({ seed, size = 92 }: Props) {
  const next = rng(seed);
  const palette = PALETTES[seed % PALETTES.length];
  const bands = 4 + Math.floor(next() * 3);

  const shapes = Array.from({ length: bands }, (_, i) => ({
    key: i,
    x: next() * size * 0.4,
    y: (i / bands) * size,
    width: size,
    height: size / bands,
    fill: palette[Math.floor(next() * palette.length)],
    opacity: 0.5 + next() * 0.5,
  }));

  const cx = size * (0.3 + next() * 0.4);
  const cy = size * (0.25 + next() * 0.35);

  return (
    <svg
      className="portrait"
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      role="img"
      aria-label="Abstract placeholder mark. No likeness is depicted."
    >
      <rect width={size} height={size} fill={palette[0]} />
      {shapes.map((s) => (
        <rect key={s.key} x={s.x} y={s.y} width={s.width} height={s.height}
              fill={s.fill} opacity={s.opacity} />
      ))}
      <circle cx={cx} cy={cy} r={size * 0.06} fill={palette[2]} opacity={0.85} />
    </svg>
  );
}
