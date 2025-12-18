export const Court = () => {
  return (
    <svg
      viewBox="-300 -50 600 500"
      width="100%"
      style={{ background: "#0b0c10", borderRadius: 8 }}
    >
      <g stroke="#d8d8d8" strokeWidth={2} fill="none">
        {/* Outer lines */}
        <rect x="-250" y="-47.5" width="500" height="470" />
        {/* 3pt arc */}
        <path d="M -220 -47.5 L -220 92.5" />
        <path d="M 220 -47.5 L 220 92.5" />
        <path d="M -220 92.5 A 220 220 0 0 0 220 92.5" />
        {/* Key */}
        <rect x="-80" y="-47.5" width="160" height="190" />
        <rect x="-60" y="-47.5" width="120" height="190" />
        {/* Free throw arc */}
        <path d="M -60 142.5 A 60 60 0 0 0 60 142.5" />
        {/* Restricted area */}
        <path d="M -40 0 A 40 40 0 0 0 40 0" />
        {/* Hoop */}
        <circle cx="0" cy="0" r="7.5" />
        {/* Backboard */}
        <rect x="-30" y="-7.5" width="60" height="-1" />
        {/* Center arc (half) */}
        <path d="M -60 422.5 A 60 60 0 0 0 60 422.5" />
      </g>
    </svg>
  );
};

