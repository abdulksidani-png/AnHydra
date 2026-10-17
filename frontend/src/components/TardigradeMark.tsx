/**
 * Original line-drawn mark: a segmented body with legs and a hint of the
 * ruled "record" lines running through it. Decorative, so hidden from
 * assistive tech — the masthead text carries the meaning.
 */
export function TardigradeMark() {
  return (
    <svg className="masthead__mark" viewBox="0 0 96 52" aria-hidden="true">
      <g
        fill="none"
        stroke="var(--forest)"
        strokeWidth={2.2}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M14 26 C14 14, 26 10, 40 10 L66 10 C80 10, 88 16, 88 26 C88 36, 80 42, 66 42 L40 42 C26 42, 14 38, 14 26 Z" />
        <path d="M26 42 L22 50 M40 42 L37 50 M54 42 L52 50 M68 42 L67 50" />
        <path d="M26 10 L22 3 M40 10 L37 3 M54 10 L52 3 M68 10 L67 3" />
        <path d="M14 26 L5 22 M14 26 L5 31" />
        <path
          d="M34 20 L56 20 M34 26 L60 26 M34 32 L56 32"
          stroke="var(--ochre)"
          strokeWidth={1.6}
        />
      </g>
    </svg>
  );
}
