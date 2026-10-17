interface FieldNotesProps {
  explanation: string;
}

/**
 * The plain-language readout. The backend returns one block of prose — from
 * Gemini, or from the offline template when Gemini is unavailable — and does
 * not say which. So this labels it by what it is, without claiming a source
 * the response doesn't carry. (If the model owner adds an
 * `explanation_source` field, label it precisely here.)
 */
export function FieldNotes({ explanation }: FieldNotesProps) {
  const paragraphs = explanation
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter(Boolean);

  return (
    <section className="card" aria-labelledby="notes-heading">
      <p className="card__label" id="notes-heading">
        Readout
      </p>
      {paragraphs.map((paragraph, index) => (
        <p className="notes__para" key={index}>
          {paragraph}
        </p>
      ))}
      <p className="notes__source">Readout of the family score and separate auxiliary biophysical signals</p>
    </section>
  );
}
