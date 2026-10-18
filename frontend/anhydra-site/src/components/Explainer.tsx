export function Explainer() {
  return (
    <section className="idle" aria-label="About this tool">
      <div className="idle-col">
        <h2>What this is</h2>
        <ol className="steps">
          <li>
            <span className="step-n mono">1</span>
            <div>
              <h3>Paste a sequence</h3>
              <p>Raw amino-acid letters or one FASTA record, 20 to 1022 residues.</p>
            </div>
          </li>
          <li>
            <span className="step-n mono">2</span>
            <div>
              <h3>A protein language model reads it</h3>
              <p>
                ESM-2, kept frozen, turns the sequence into an embedding. A classifier trained on 3,151 sequences turns
                that into a score from 0 to 1.
              </p>
            </div>
          </li>
          <li>
            <span className="step-n mono">3</span>
            <div>
              <h3>You get a call and the evidence</h3>
              <p>
                The score asks whether the sequence belongs to the desiccation-protective families. It does not measure
                how much a protein protects. Use it to decide what to test first.
              </p>
            </div>
          </li>
        </ol>
      </div>
      <div className="idle-col">
        <h2>Why it is worth trusting</h2>
        <div className="trust-fig">
          <p className="mono big glow-text">0.818</p>
          <p>
            AUC on a protein family the model had never seen, where a classical BLAST search gets 0.739. When a close
            relative exists, alignment ties the model. When none exists, only the model still works.
          </p>
        </div>
        <ul className="trust-list">
          <li>
            <strong>The K-segment.</strong> A CNN trained from scratch, with no motif database, rediscovered the
            dehydrin K-segment on its own. It is the published motif that defines the family.
          </li>
          <li>
            <strong>Four confounds were tested</strong> against the result before it was reported.
          </li>
          <li>
            <strong>Disorder is the point.</strong> These proteins have no stable 3D shape. That is the mechanism, so
            the page never draws a confident fold for them.
          </li>
        </ul>
      </div>
    </section>
  );
}
