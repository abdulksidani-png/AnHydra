interface ClosestRecordProps {
  nearestHomolog: string | null;
}

/**
 * The backend returns one sequence_id — the nearest known protective sequence
 * by cosine similarity in ESM-2 space. It is NOT an alignment, so this card
 * deliberately shows no identity, coverage or E-value: those would imply a
 * BLAST-style comparison that didn't happen.
 */
export function ClosestRecord({ nearestHomolog }: ClosestRecordProps) {
  if (!nearestHomolog) {
    return (
      <section className="card" aria-labelledby="record-heading">
        <p className="card__label" id="record-heading">
          Nearest protective sequence
        </p>
        <p className="record__note">
          No nearest protective sequence was returned. The determination rests
          on sequence character alone.
        </p>
      </section>
    );
  }

  const looksLikeAccession = /^[A-NR-Z][0-9][A-Z0-9]{3}[0-9]$|^[OPQ][0-9][A-Z0-9]{3}[0-9]$/.test(
    nearestHomolog,
  );

  return (
    <section className="card" aria-labelledby="record-heading">
      <p className="card__label" id="record-heading">
        Nearest protective sequence
      </p>
      <p className="record__id">
        {looksLikeAccession ? (
          <a
            href={`https://www.uniprot.org/uniprotkb/${nearestHomolog}`}
            target="_blank"
            rel="noreferrer"
          >
            {nearestHomolog}
          </a>
        ) : (
          nearestHomolog
        )}
      </p>
      <p className="record__note">
        Closest training-set protective sequence by cosine similarity of the
        ESM-2 embedding — a neighbourhood in the model's representation, not a
        sequence alignment. Treat it as orientation, not as evidence of
        homology.
      </p>
    </section>
  );
}
