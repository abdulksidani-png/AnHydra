import { useId, type KeyboardEvent as ReactKeyboardEvent } from 'react';
import { cleanSequence } from '../api/client';
import { EXAMPLES } from '../api/mock';

interface SequenceInputProps {
  value: string;
  onChange: (next: string) => void;
  onSubmit: () => void;
  isLoading: boolean;
}

export function SequenceInput({
  value,
  onChange,
  onSubmit,
  isLoading,
}: SequenceInputProps) {
  const fieldId = useId();
  const residueCount = cleanSequence(value).length;

  function handleKeyDown(event: ReactKeyboardEvent<HTMLTextAreaElement>) {
    // Cmd/Ctrl+Enter submits — worth having when you are demoing live.
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
      event.preventDefault();
      if (!isLoading) onSubmit();
    }
  }

  return (
    <section className="card card--tight" aria-labelledby={`${fieldId}-label`}>
      <label className="input__label" id={`${fieldId}-label`} htmlFor={fieldId}>
        Enter a sequence to identify (20–1,022 residues)
      </label>

      <textarea
        id={fieldId}
        className="input__field"
        rows={4}
        spellCheck={false}
        autoCapitalize="characters"
        placeholder="Paste amino-acid residues or a FASTA record…"
        value={value}
        disabled={isLoading}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
        aria-describedby={`${fieldId}-count`}
      />

      <div className="input__footer">
        <button
          type="button"
          className="btn btn--primary"
          onClick={onSubmit}
          disabled={isLoading || residueCount === 0}
        >
          {isLoading ? 'Identifying…' : 'Identify'}
        </button>
        <button
          type="button"
          className="btn btn--quiet"
          onClick={() => onChange('')}
          disabled={isLoading || value.length === 0}
        >
          Clear
        </button>
        <span className="input__count" id={`${fieldId}-count`}>
          {residueCount} aa
        </span>
      </div>

      <div className="input__examples">
        <span className="input__examples-label">Or try a known sequence:</span>
        {EXAMPLES.map((example) => (
          <button
            key={example.id}
            type="button"
            className="btn btn--chip"
            disabled={isLoading}
            onClick={() => onChange(example.sequence)}
          >
            {example.label}
            <span className="btn__blurb">{example.blurb}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
