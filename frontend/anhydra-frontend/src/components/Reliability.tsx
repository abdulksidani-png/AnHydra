import { EVALUATION } from '../evals';

/**
 * The two-tier eval table — the AI-track centerpiece.
 *
 * Numbers come from src/evals.ts, not from /score, because they describe the
 * model rather than this sequence. The sanity rows are de-emphasised and the
 * caveat renders directly under the table, so the honest reading is the easy
 * one.
 */
export function Reliability() {
  const { rows, protocol, caveat, lastUpdated } = EVALUATION;

  return (
    <section className="card" aria-labelledby="reliability-heading">
      <p className="card__label" id="reliability-heading">
        How well the model does
      </p>
      <p className="card__lede">{protocol}</p>

      <div className="table-scroll">
        <table className="table">
          <thead>
            <tr>
              <th scope="col">Question asked</th>
              <th scope="col">Model</th>
              <th scope="col" className="num">
                ROC-AUC
              </th>
              <th scope="col" className="num">
                PR-AUC
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr
                key={`${row.task}-${row.model}-${index}`}
                className={row.tier === 'sanity' ? 'is-sanity' : undefined}
              >
                <td>{row.task}</td>
                <td>{row.model}</td>
                <td className="num num--strong">{row.rocAuc.toFixed(3)}</td>
                <td className="num">
                  {row.prAuc === null ? (
                    <span className="num--absent" title="not recorded yet">
                      —
                    </span>
                  ) : (
                    row.prAuc.toFixed(3)
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {caveat && (
        <p className="eval__caveat">
          <strong>Read these with the caveat.</strong> {caveat}
        </p>
      )}

      <p className="notes__source">evals last updated {lastUpdated}</p>
    </section>
  );
}
