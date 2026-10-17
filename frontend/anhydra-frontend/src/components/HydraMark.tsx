/**
 * The AnHydra mark: three necks rising from a coiled body, drawn in one
 * continuous line weight. The heads are serpent-and-polyp at once — a nod to
 * both the myth the name borrows and the cnidarian that shares it.
 *
 * Decorative, so hidden from assistive tech; the wordmark beside it carries
 * the meaning.
 */
export function HydraMark() {
  return (
    <svg className="masthead__mark" viewBox="0 0 92 58" aria-hidden="true">
      <g
        fill="none"
        stroke="var(--glow)"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        {/* coiled body */}
        <path d="M8 50 C8 42, 18 38, 30 38 L62 38 C74 38, 84 42, 84 50" />
        <path d="M14 50 C14 45, 22 43, 32 43 L60 43 C70 43, 78 45, 78 50" />

        {/* left neck */}
        <path d="M30 38 C24 30, 22 20, 28 13" />
        <path d="M28 13 C31 8, 38 9, 38 14 C38 18, 33 20, 29 18" />

        {/* centre neck, tallest */}
        <path d="M46 38 C44 27, 44 15, 47 7" />
        <path d="M47 7 C50 2, 58 3, 58 9 C58 13, 52 16, 48 13" />

        {/* right neck */}
        <path d="M62 38 C68 31, 70 22, 65 15" />
        <path d="M65 15 C68 10, 75 11, 75 16 C75 20, 69 22, 66 19" />
      </g>

      {/* water line through the body — the thing being lost */}
      <g stroke="var(--silt-deep)" strokeWidth={1.4} strokeLinecap="round" fill="none">
        <path d="M24 46 L40 46 M48 46 L68 46" />
      </g>
    </svg>
  );
}
