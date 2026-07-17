# Project rules

## Purpose and sources of truth

- Find global buyers of `tape` and `masking film`, with Europe and North America prioritized.
- `deliverables/tape-masking-film-customer-master.xlsx` is the only customer-facing master table.
- `data/processed/company-master.json` is the workbook's structured input. Files under `data/raw/` are immutable evidence.

## Data rules

- Keep exactly one row per `company_id`; do not merge different company IDs silently.
- Count an email as valid only when its validation status is `1`.
- Treat company-level coverage as the business metric: 50 companies with any valid contact, 39 with a valid email, and 41 with a valid phone.
- Report the coverage split as 30 with both, 9 email-only, 11 phone-only, and 0 with neither.
- Use ¥2.10 per company with any valid contact, ¥2.69 per valid-email company, and ¥2.56 per valid-phone company. These are alternative views and must not be added.
- Keep 46 globally deduplicated valid email strings and 49 company-email associations as technical audit counts, not business KPIs.
- Preserve source URLs and raw API fields. Never invent missing contact details.
- Localize business-facing workbook values into Chinese: `tape` = `胶带`, `masking film` = `遮蔽膜`; use the same Chinese terms for categories and search terms.
- Prefer Chinese country and product terminology in the workbook, but preserve company names, contact details, URLs, trade descriptions, addresses, business scopes, model numbers, and uncertain terms in their original form.

## Paid API and secrets

- Paid scripts must default to dry-run and require an explicit execution flag.
- Do not exceed the current cumulative cap of ¥200 without new user approval. Current audited spend is ¥105.10.
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
