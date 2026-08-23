export function RiftAtmosphere() {
  return (
    <div
      className="rift-atmosphere"
      data-testid="rift-atmosphere"
      aria-hidden="true"
    >
      <div className="rift-atmosphere__glow" />
      <svg className="rift-map" viewBox="0 0 1600 1100" preserveAspectRatio="xMidYMid slice">
        <defs>
          <linearGradient id="lane-energy" x1="0" y1="1" x2="1" y2="0">
            <stop offset="0" stopColor="#2fd9d0" stopOpacity="0" />
            <stop offset="0.5" stopColor="#58eee5" stopOpacity=".58" />
            <stop offset="1" stopColor="#d6b96a" stopOpacity="0" />
          </linearGradient>
          <radialGradient id="core-energy">
            <stop offset="0" stopColor="#d6b96a" stopOpacity=".8" />
            <stop offset=".3" stopColor="#4ee0d6" stopOpacity=".28" />
            <stop offset="1" stopColor="#4ee0d6" stopOpacity="0" />
          </radialGradient>
          <filter id="soft-glow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="8" />
          </filter>
          <pattern id="field-grid" width="64" height="64" patternUnits="userSpaceOnUse">
            <path d="M64 0H0V64" fill="none" stroke="#70ddd6" strokeOpacity=".045" />
          </pattern>
        </defs>
        <rect width="1600" height="1100" fill="url(#field-grid)" />
        <g className="rift-map__contours" fill="none">
          <path d="M-80 905C165 708 292 736 455 585s226-307 428-310 302 101 534-24 344-247 407-318" />
          <path d="M-44 1000C191 799 344 827 520 667s217-272 410-278 333 86 515-50 315-236 425-271" />
          <path d="M-130 772C88 617 229 633 391 489s276-331 477-329 298 126 519 3 328-223 421-263" />
          <path d="M-32 1100c291-167 456-139 625-275s245-256 441-230 261 111 434 27 275-166 384-164" />
          <path d="M214-106c119 150 144 256 115 392s-9 269 134 353 287 69 393 207 118 237 147 358" />
          <path d="M413-85c72 122 84 226 43 346s-13 220 96 295 247 90 338 226 92 234 127 369" />
        </g>
        <g className="rift-map__lanes" fill="none" stroke="url(#lane-energy)">
          <path className="rift-lane rift-lane--top" d="M180 890C270 610 296 332 523 206s554-48 899-96" />
          <path className="rift-lane rift-lane--mid" d="M177 897 795 552l629-446" />
          <path className="rift-lane rift-lane--bot" d="M183 905c268-24 541-31 746-184s288-392 498-612" />
        </g>
        <g className="rift-map__nodes">
          <circle cx="178" cy="898" r="72" fill="url(#core-energy)" filter="url(#soft-glow)" />
          <circle cx="178" cy="898" r="9" />
          <circle cx="798" cy="550" r="6" />
          <circle cx="1426" cy="108" r="8" />
        </g>
      </svg>
      <div className="coach-core">
        <span className="coach-core__orbit" />
        <span className="coach-core__orbit coach-core__orbit--inner" />
        <span className="coach-core__point" />
      </div>
    </div>
  )
}
