# Project rules

## Purpose and sources of truth

- Find global buyers of tape, masking film, brushes, hog-bristle brushes, wool brushes, PVC corner guards, and plastic buckets, with Europe and North America prioritized.
- `deliverables/客户表（7.17）.xlsx` is the only customer-facing master table.
- `data/processed/company-master.json` is the workbook's structured input. Files under `data/raw/` are immutable evidence.

## Data rules

- Keep exactly one row per `company_id`; do not merge different company IDs silently.
- Count an email as valid only when its validation status is `1`.
- Treat company-level coverage as the business metric: 270 companies with any valid contact, 205 with a valid email, and 210 with a valid phone.
- Report the coverage split as 145 with both, 60 email-only, 65 phone-only, and 0 with neither.
- Use ¥1.43 per company with any valid contact, ¥1.89 per valid-email company, and ¥1.84 per valid-phone company. These are alternative views and must not be added.
- Keep 301 globally deduplicated valid email strings and 308 company-email associations as technical audit counts, not business KPIs.
- Preserve source URLs and raw API fields. Never invent missing contact details.
- Localize business-facing workbook values into Chinese: `tape` = `胶带`, `masking film` = `遮蔽膜`; use the same Chinese terms for categories and search terms.
- Prefer Chinese country and product terminology in the workbook. The workbook's business-scope column must contain Chinese only; preserve its API original in `company-master.json` and raw evidence. Preserve company names, contact details, URLs, trade descriptions, addresses, model numbers, and uncertain terms in their original form.

## Paid API and secrets

- Paid scripts must default to dry-run and require an explicit execution flag.
- Do not exceed the current cumulative cap of ¥500 without new user approval. Current audited spend is ¥387.10.
- Do not retry email status `0` or `3` blindly. Prefer a new official source, a relevant person, or a real delivery test.
- Read the API key only from `UPKUAJING_API_KEY`; never commit it.

## Storage and workflow

- Maintained code belongs in `src/` and `scripts/`; tests in `tests/`; business deliverables in `deliverables/`.
- Use `work/` and `output/` only for disposable local artifacts; both remain untracked.
- Do not create parallel workbook copies such as `final-v2` or `new`.
- Rebuild the workbook from the maintained `company-master.json` as documented in `README.md`.
- Do not run all historical processing scripts as a full rebuild chain; it is incomplete and can degrade the maintained master.

## Verification and version control

- Run `PYTHONPATH=src python3 -m unittest discover -s tests -v` after relevant changes.
- Rebuild the workbook after changing its generator or processed data, then inspect the rendered preview and formula-error scan.
- Every project modification must be committed and pushed in a small, verifiable commit. Finish with local `HEAD` equal to `origin/main`.

## Documentation map

- `README.md`: setup, directory contract, and reproducible rebuild.
- `docs/api-research.md`: API endpoints and measured behavior.
- `docs/cost-analysis.md`: cost definitions and optimization decisions.
- `docs/handoff.md`: current state and developer handoff.
