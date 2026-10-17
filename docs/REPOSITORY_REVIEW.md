# Repository review — October 17, 2026

Reviewed snapshot: `410b8c9`. **Historical audit: see RELEASE.md for subsequent fixes and remaining gates.** This is an analysis report; application, training, deployment, and GitHub configuration were not changed during this review.

## Scope and verification

Every tracked file in this snapshot is covered in the inventory below. Python, inline JavaScript, shell scripts, configuration, documentation, CSV artifacts, and the three committed figures were inspected. Binary figures were visually inspected; CSVs were checked for structure and selected numerical consistency. This does not establish that experiments can be reproduced from the original raw data.

- Existing suite: **27 passed**, one Starlette/httpx deprecation warning. Command: `.venv/Scripts/python.exe -m pytest -q --basetemp=.tmp/review-tests-unrestricted`. Sandbox filesystem restrictions initially caused fixture errors and a stalled rerun; the unrestricted run completed in 4.75 seconds.
- Inline JavaScript passed a Node syntax check. This was not a browser interaction or accessibility test.
- Isolated synthetic reproductions confirmed incorrect embedding hashes are accepted by training and evaluation, and CNN validation splitting can produce single-class partitions. Reproduction script is local at `.tmp/review_repro.py`.
- Public GitHub Actions API returned zero workflow runs; no workflow files are tracked.
- No live deployment, external data pulls, model downloads, training on real data, or Gemini requests were performed. Torch is absent from this local environment, so the actual neural-network paths were not executed. Caddy and Linux systemd configuration were reviewed statically.

## Findings, ordered by impact

### 1. High: cache validity is enforced only when embedding is rerun

Locations: `src/tardiscreen/model.py:75`, `src/tardiscreen/evaluate.py:70`, `scripts/backfill_embedding_hashes.py:46`.

`embed._load_cache()` verifies sequence hashes, but production training and evaluation load the NPZ directly and align solely by accession. If a sequence changes under an existing ID and someone skips the embed step, both consumers accept the old vector for the new sequence. Synthetic data with deliberately wrong hashes successfully trained a model and loaded into evaluation. This can silently invalidate both the score model and the reported comparison.

The migration script has a related provenance problem: equality of ID sets cannot prove that the sequences used to compute old embeddings equal today's sequences. It stamps current hashes onto legacy vectors without independent sequence provenance. Duplicate dataset IDs are also collapsed by `dict(zip(...))` before checking.

Recommended fix: share a lightweight NPZ validator across training and evaluation. Require unique IDs, aligned shapes, finite vectors, a model identifier, and matching sequence hashes; reject stale rows with an actionable re-embed message. Legacy hash migration should require verified historical inputs rather than infer correctness from IDs alone.

### 2. High: long inputs are represented differently by the two models without disclosure

Locations: `app/main.py:28`, `src/tardiscreen/embed.py:65`, `app/static/index.html:624`.

The API accepts 10,000 residues, but tokenization truncates to 1,024 tokens, including special tokens. The ESM score therefore uses only a prefix, while biophysical features, motifs, and the UI specimen length use the full input. Two sequences with the same encoded prefix can receive the same ESM representation despite very different tails. The page says the language model reads the whole sequence.

Recommended fix: expose the scoring limit and reject longer inputs, or implement and evaluate a deliberate windowing policy. Report the effective modeled length separately from full-sequence visualizations. Windowing changes representations and requires compatible training/evaluation.

### 3. Medium: experiment scripts do not enforce the same matched population

Locations: `blast_baseline.py:153`, `cnn.py:168`, `family_holdout.py:120`, `motifs.py:110`, `remote_homology.py:44` under `src/tardiscreen/`.

The main evaluator requires `in_matched_set` for the real task. These five consumers filter only if the column happens to exist; otherwise they silently include unmatched positives. An older or malformed dataset can thus produce apparently comparable numbers from different populations. Use `evaluate.task_subset()` everywhere and test the missing-column case.

### 4. Medium: the offline explanation misattributes the ESM score

Location: `src/tardiscreen/explain.py:107`.

The online prompt correctly distinguishes auxiliary biophysical contributions from the ESM prediction. The offline template instead says the ESM score is “driven mainly by” those features and drops their signs. A synthetic 0.90 score with a -4.0 contribution describes that opposing feature as a driver of the positive result. This is also the default experience when no Gemini key is configured.

Recommended fix: state that these are supporting/opposing signals from a separate auxiliary classifier. Preserve sign and avoid claiming measured protection or explaining the ESM model with another model's coefficients.

### 5. Medium: CNN early stopping can select against a single-class validation set

Location: `src/tardiscreen/cnn.py:75`.

`_split_val()` shuffles clusters without labels. It can leave a class out of validation or training. A two-cluster synthetic example produced training `[0]`, validation `[1]`. `train_fold()` substitutes AUC 0.5 for a single-class validation set; all epochs then tie and the first epoch is retained. Outer CV guards do not guarantee a valid inner split.

Recommended fix: construct inner cluster-disjoint partitions containing both classes, with explicit minimum-cluster checks. Fail clearly when impossible. Separately, choose the truncation length from training data within each outer fold; the current percentile sees test lengths.

### 6. Medium: committed artifacts and narrative describe different dataset stages

Locations: `docs/results/dataset_summary.md`, `docs/METHODS.md`, `README.md`, `docs/results/confusion_matrix.png`.

The summary describes the original 4,277-row dataset containing 1,604 `other_idp` negatives. The final remote-homology artifact and confusion matrix contain **1,049 rows: 529 protective and 520 negatives**. Methods and demo copy describe 529 matched pairs. Nine negatives were lost or excluded somewhere after matching; the committed artifacts alone do not identify the stage. The summary writer only knows the original label list and is not rerun by the merge script.

Recommended fix: publish stage-specific counts and regenerate a final summary after clustering/embedding, including matched pairs retained together and balance after exclusions. Store a dataset fingerprint, code revision, encoder revision, and split IDs beside each result. Do not invent a corrected total from partial artifacts.

### 7. Medium: readiness is reported from file existence

Locations: `app/main.py:94`, `app/static/index.html:471`, `scripts/check_site.sh:35`.

`model_trained` checks only whether a path exists. A corrupt bundle, missing model name, missing Torch installation, or unavailable encoder weights still yields a green “model loaded” label. The scoring smoke test catches many of these later, but the UI does not.

Recommended fix: distinguish liveness, artifact presence, and inference readiness. A readiness check should validate the bundle and required runtime, with encoder warmup handled deliberately rather than downloading weights on every health request.

### 8. Medium: browser keyboard shortcuts bypass the disabled submit button

Location: `app/static/index.html:482` and the textarea keydown listener.

The click button is disabled during scoring, but Ctrl/Cmd+Enter calls `run()` directly. There is no in-flight guard. Repeated shortcuts can launch concurrent expensive CPU inference, and an earlier response can replace a newer result. Add a shared busy guard or cancellation/request-order mechanism used by every entry point.

### 9. Medium: coverage cannot refresh the current merged dataset

Location: `src/tardiscreen/coverage.py:150`.

The command searches only `other_idp` negatives and returns before fetching positives if it finds no matching DisProt rows. After `merge_dataset` replaces that tier with `idp_matched`, rerunning coverage does not refresh either class. Existing CSVs can remain stale while the command exits successfully. Preserve source-aware coverage records for current IDs, and distinguish an explicitly historical diagnostic mode from the current pipeline command.

### 10. Medium: documentation overstates what the experiments establish

Locations: README family-holdout discussion; `docs/DEMO.md`; `docs/EXPLAINER.md`; `family_holdout.py` introductory claims.

Holding out a name-assigned family and its sequence clusters does not establish that every evolutionary relative is absent from training. The repository itself acknowledges LEA/dehydrin relatedness. Likewise, a chance shuffled-label result does not prove every kind of leakage is absent, and low mean differences do not prove covariates contain no residual predictive information. AUC is a ranking measure, not classification accuracy.

The score is described in `model.py` as calibrated, but the implementation fits class-weighted logistic regression without a calibration procedure or calibration evaluation. The auxiliary model is advertised as a fallback for embedding failures, but `predict()` has no such fallback.

Recommended fix: describe exactly the tested split and measured uncertainty, remove unsupported calibration/fallback claims, and keep the documented taxonomic and related-family limitations visible. Scientific citations and event rules were not independently verified in this code review.

## Additional reliability issues

- Embedding checkpoints and production bundles are written directly to their destination. An interrupted write can destroy the usable prior artifact; write to a temporary sibling and replace atomically after validation.
- Dataset and embedding acceptance checks return booleans that command entry points ignore. Automated pipelines can receive a zero exit status after failed acceptance checks.
- `match_negatives.main()` leaves earlier output files in place when no pairs are found. Downstream commands can consume stale results unless run provenance is tracked.
- `build_negatives.attach_sequences()` fills the sequence but retains the MobiDB length value, including a possible zero or an outdated length. Matching trusts that field. Recompute length from the fetched sequence, and handle changed disorder-annotation sequence versions explicitly.
- `merge_dataset` flags membership by ID rather than retaining pair identifiers. Clustering can remove one partner without removing the other, so pre-clustering balance is not a guarantee for the evaluated population.
- `explain.TIMEOUT_S` parses environment input during import. An invalid value can stop the whole app before the external-API fallback is available.
- `blast_baseline` calls `(oof != 0.5)` a hit rate. Equal positive/negative best scores can produce 0.5 despite real hits; record hit presence directly. The 50-target cap can also censor the weaker class's best hit in a dense family.
- `diagnose.check_source_confound()` labels a task clean whenever the class source sets overlap. Overlap alone does not rule out large source-distribution differences; its closing narrative also still describes the retired DisProt task.
- `probe_sources` expects whole-document JSON from MobiDB, while the actual fetcher supports JSONL. The probe can reject a response that the fetcher could consume.
- No GitHub CI runs the passing test suite. Dependencies have lower bounds but no tested constraints file; model weights are selected by name without a recorded immutable revision.

## File-by-file inventory

Each row records the file's purpose, review conclusion, and the most useful next action. “No specific defect found” means static review found none within this scope, not a guarantee.

| File | Analysis |
| --- | --- |
| `.env.example` | Contains an empty key and optional model name, no actual credential. Document timeout configuration and validate it at runtime. Model availability was not queried. |
| `.gitignore` | Covers the current key file, raw artifacts, virtualenv, caches, retired frontend outputs, and local screenshot. Other secret naming conventions are not covered; no claim about full Git-history secret scanning. |
| `CONTRIBUTING.md` | Clear roles and PR workflow. Definition-of-done AUC expectations predate actual results; separate historical targets from acceptance criteria. Event rules remain unverified. |
| `LICENSE` | Standard MIT text and project attribution; no specific content defect found. This does not address upstream dataset/model licensing. |
| `README.md` | Strong architecture and limitation overview; rounded main result values agree with CSVs. Correct family-holdout certainty, calibrated-probability implications, missing embedding fallback, and current pair counts. The architecture implies 101,057 trainable parameters (704 embedding + 98,816 convolutions + 1,024 batch-normalization + 513 output), consistent with the approximate 101k claim. |
| `app/__init__.py` | Empty package marker; no specific defect found. |
| `app/main.py` | Input parsing rejects invalid symbols and multiple FASTA records; missing model returns 503 and tests pass. Address truncation disclosure and readiness. Prediction/runtime failures currently propagate as generic server errors. |
| `app/static/index.html` | Inline JS parses; output strings generally use textContent or escaping. Handles API failures and reduced-motion animation. Address keyboard request overlap, truncation copy, explanation provenance heuristic, and accessibility announcements for errors/results. This review did not test browser layout. |
| `data/README.md` | Outdated: says `embeddings.npy` rather than `embeddings.npz` and implies all outputs regenerate from `data.py`. Document the full staged pipeline and distinguish raw data, caches, models, and result exports. |
| `deploy/Caddyfile.anhydra` | Domain/www and explicit HTTP IP block proxy the current FastAPI page and API together. No stale static root remains. Requires real DNS/ports and Caddy validation on the server. |
| `deploy/Caddyfile.template` | Minimal domain reverse proxy matches current app routing; placeholder must be rendered. No specific static defect found. |
| `deploy/README.md` | Current architecture instructions are correct; historical server state is clearly dated. Reconcile historical missing-model observations with present readiness before claiming live acceptance. |
| `deploy/tardiscreen.service.template` | Localhost binding, one worker, dynamic user, read-only checkout and separate writable cache are coherent. Linux mount permissions, venv portability, memory headroom and cached encoder availability remain unverified. |
| `docs/DEMO.md` | Useful operational and backup plan. Fixed example scores are not guaranteed; holdout and leakage wording is stronger than evidence. Say what the actual response shows. |
| `docs/EXPLAINER.md` | Accessible project narrative, but simplifies clustering to a pairwise guarantee and says an uncatalogued organism necessarily has no database relatives. Qualify those statements and the AUC/accuracy wording. |
| `docs/METHODS.md` | Explicitly acknowledges taxonomic confounding, permissive clustering and related holdouts. Update final population counts, temper “ruled out” language, and record reproducibility metadata. |
| `docs/SUBMISSION.md` | Actionable checklist; no software defect found. Deadline, track rules, sponsor eligibility, and completion status were not externally verified. |
| `docs/results/blast_results.csv` | Numeric metrics are valid ranges and align with README rounding. Hit-rate meaning is inaccurate in the producer; no per-fold provenance is included. |
| `docs/results/cnn_motifs.csv` | 48 rows, 12 per kernel width, consistent with exporter settings. Filter AUCs are descriptive in-sample rankings, not independent generalization evidence; preserve that distinction. |
| `docs/results/cnn_results.csv` | Two task rows with finite valid metrics, matching README rounding. Cannot retrain locally without Torch/raw data; inner-split issue needs resolution before regeneration. |
| `docs/results/confusion_matrix.png` | Visually legible; 496 true negatives, 24 false positives, 23 false negatives, 506 true positives. Totals agree with the 1,049-row remote artifact, not 529 complete pairs. |
| `docs/results/dataset_summary.md` | Historical original dataset summary, currently presented without a stage label. It is not the final matched evaluation dataset. |
| `docs/results/disorder_coverage.csv` | Contains 1,604 `other_idp` and 1,069 protective records. This is an input-stage artifact, not coverage for the replacement 520-negative evaluation tier. |
| `docs/results/family_holdout.csv` | LEA/dehydrin rows agree with headline rounded results; negative counts are 249 and 271. No per-sequence predictions or uncertainty estimates accompany these holdouts. |
| `docs/results/feature_importance.png` | Visually legible signed auxiliary coefficients. Positive hydropathy and negative serine/low-complexity coefficients deserve interpretation against generic UI claims about protective signatures; they do not explain the ESM classifier. |
| `docs/results/remote_homology.csv` | 1,049 rows, 529 positives and 520 negatives. Pooled AUCs recompute to BLAST 0.981656 and ESM-2 0.990555. These need not equal mean-fold AUCs. Missing IDs/fold labels limit auditing. |
| `docs/results/results_auc.png` | Readable and consistent with the three model CSV rows. Displays only composition, biophysical, ESM-2; it is not the complete five-model README comparison. |
| `docs/results/results_table.csv` | Six valid task/model rows; rounded values match Markdown. Include dataset/split fingerprint before treating it as reproducible evidence. |
| `docs/results/results_table.md` | Matches CSV rounding; no specific formatting defect found. |
| `notebooks/.gitkeep` | Empty directory placeholder; no runtime behavior. |
| `pyproject.toml` | Src-layout package and dev/ML extras are coherent for checkout-based use. `app` is not included by `where = ["src"]`; a built wheel alone does not contain the web app/page. Document checkout deployment or package app assets deliberately. |
| `requirements.txt` | Includes editable project and repeats most dependencies. Full ML installation is large; pytest is only in the dev extra. Document the test install and record a tested dependency set. |
| `scripts/backfill_embedding_hashes.py` | See finding 1: ID equality is insufficient sequence provenance. Also validate dataset duplicate IDs and array shapes before migration. |
| `scripts/check_site.sh` | Exercises actual scoring in addition to health. Synthetic Gly/Ser richness is not an experimentally verified positive, so its 0.5 threshold is a model expectation rather than proof of correctness. Gemini attribution is inferred from text and can misclassify provenance. |
| `scripts/collect_results.sh` | Copies only an explicit artifact allowlist. Missing inputs are reported but old destination files remain, allowing mixed-run exports; use manifests and stage-specific outputs. |
| `src/tardiscreen/__init__.py` | Version and package description are straightforward; no specific defect found. |
| `src/tardiscreen/blast_baseline.py` | Correctly constructs each database from training rows. Address shared-population validation, hit-rate calculation, and class-hit censoring. BLAST itself was not executed. |
| `src/tardiscreen/build_negatives.py` | Whole-word acronym filtering fixes the known nuclear/LEA issue. Handles JSONL and multiple sources. Address fetched-sequence lengths, source-layer provenance, stale outputs on empty results, and first-page-only query rejection. |
| `src/tardiscreen/cnn.py` | Outer folds share the evaluator's cluster splitter. Inner split lacks class checks; padding is included in batch normalization and global pooling, so padding/boundary effects can carry length information. Evaluate masking before architectural changes; changes require rerunning metrics. |
| `src/tardiscreen/coverage.py` | Interval clipping/merging has a passing regression test. Current refresh behavior remains tied to the retired negative tier; `_uniprot_spans` also filters description without explicitly requiring feature type Region. |
| `src/tardiscreen/data.py` | Cleans, deduplicates, resolves conflicting labels and clusters across tiers. Greedy fallback is explicitly provisional but downstream artifacts do not preserve its provenance. Acceptance failures do not fail the CLI; fetch failures can overwrite an existing dataset with partial/empty data. |
| `src/tardiscreen/diagnose.py` | Shared `task_subset` is used for primary diagnostics. Source overlap is an inadequate cleanliness criterion; strict-disorder mode and closing narrative still target the original experiment. Avoid treating one shuffle as proof of no leakage. |
| `src/tardiscreen/embed.py` | Model selection and cache hash invalidation are regression-tested. Address truncation, direct checkpoint writes, failure exit status, immutable encoder revision, and special-token pooling (attention masking also pools BOS/EOS). Changing pooling invalidates existing vectors/models. |
| `src/tardiscreen/evaluate.py` | Scaler is fit within folds, cluster IDs are validated, OOF predictions cover test partitions, and main task filtering fails clearly. Add cache integrity checks and persisted splits; data rows missing embeddings are dropped, changing the matched population. |
| `src/tardiscreen/explain.py` | HTTP failures, blocked candidates, thought filtering and secret-safe logging have passing tests. Fix offline attribution and import-time timeout parsing. The prompt's distinction between family triage and efficacy is useful. |
| `src/tardiscreen/family_holdout.py` | Excludes all test clusters from training, including cross-family clusters. Family names come from annotations, not an evolutionary proof; cache freshness and silent incomplete family downloads need handling. Reuse strict matched filtering. |
| `src/tardiscreen/features.py` | Deterministic nine-feature calculation with safe empty-sequence defaults. `gly_ser_his` is exactly the sum of three other columns, so individual correlated coefficients should not be read as independent causal explanations. No feature regression tests directly cover basic values. |
| `src/tardiscreen/match_negatives.py` | Deterministic greedy matching with no replacement, explicit calipers and balance diagnostics. Empty/no-pair runs can leave stale outputs; output omits partner IDs needed to preserve pairing downstream. Balance failure warns but still writes. |
| `src/tardiscreen/merge_dataset.py` | Removes earlier matched negatives before appending; idempotency test passes. Re-clustering can break matched pairs and backup is overwritten on every run. Preserve pair IDs and version backups; recompute balance after final filtering. |
| `src/tardiscreen/model.py` | Uses the recorded training encoder at inference and caches bundles by mtime. Address unchecked cache hashes, missing-row filtering, non-atomic save, unvalidated model metadata during training, and unsupported calibration/fallback descriptions. |
| `src/tardiscreen/motifs.py` | Provides inspectable filter windows rather than presenting them as test accuracy. Uses the CNN's fragile validation split; left-boundary windows are shortened rather than aligned to a fixed-width padded receptive field, which can distort consensus positions. |
| `src/tardiscreen/probe_sources.py` | Read-only diagnostic with bounded sample requests. Whole-document JSON parsing is inconsistent with MobiDB JSONL support in the production fetcher; network behavior unverified. |
| `src/tardiscreen/remote_homology.py` | Scores both methods on identical outer test rows, a useful paired comparison. Enforce task filtering, persist IDs/folds, and avoid interpreting an arbitrary AUC difference threshold as statistical significance/equivalence. |
| `tests/test_explain.py` | Four passing tests cover prompt semantics, successful response parsing, timeout logging, and empty candidates. Add opposing-feature offline wording, invalid timeout, malformed payload, and explicit provenance coverage. |
| `tests/test_regressions.py` | Twenty-three passing parametrized cases cover input, missing models, clustering splits, cache invalidation, model roundtrip, merge repeatability, and disk page loading. Missing: consumer hash validation, inner CNN class balance, current coverage refresh, and browser in-flight behavior. |

## Suggested order of work

1. Add shared embedding/dataset validation and strict task filtering, with focused regressions.
2. Resolve long-sequence policy and offline explanation semantics.
3. Repair inner CNN splitting and retain paired/run provenance through the data pipeline.
4. Regenerate final summaries and results only from verified inputs; qualify scientific claims.
5. Add GitHub CI for the lightweight suite and a separate explicit deployment smoke test.

No production behavior was changed and nothing from this review was committed or pushed.
