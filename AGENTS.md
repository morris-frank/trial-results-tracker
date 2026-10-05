# trial-results-tracker working agreement

The repository contract for humans and coding agents; `CLAUDE.md` links here.

## Golden rules

1. **Every published number says how it was measured.** A trial counted as unreported
   names its evidence basis (registry only, or registry plus publication search) and the
   date of the data. Naming institutions is the point of the tracker, so the method
   must be checkable.
2. **WHO standard and legal duty are separate columns, never merged.** A trial can miss
   WHO best practice without breaking any law; the site must never imply a legal breach
   it has not established.
3. **Stale registry status is not non-reporting.** Withdrawn, suspended, never-started
   and "ongoing past completion" trials are their own categories, not "unreported".
4. **Raw registry data is fetched, never committed.** `data/` and `dist/` are gitignored;
   the build is reproducible from the source and a dated snapshot.
5. **Classification is pure code with tests.** The rules that sort a trial into a
   category live in one module with a test per rule and no I/O.
6. Add dependencies with `uv add`; never hand-edit `uv.lock`.

## Layout

- `src/trial_results_tracker/`: the package; `__main__.py` is the CLI (`fetch`, `build`).
- `site/`: static assets the build copies into `dist/`.
- `sponsors/aliases.csv`: the reviewed sponsor alias table; only reviewed rows are used.
- `sponsors/disputes.csv`: open disputes, shown as per-trial notes; `CORRECTIONS.md` logs outcomes.
- `tests/`: pytest.
- `docs/`: research and plans, deleted or folded into code when done.
- `vercel.json`: the deploy. Vercel builds every push to `main`.

## Workflow

```sh
mise run setup   # cold start
mise run check   # lint + format check + tests: the definition of done
mise run fetch   # dated registry snapshot into data/raw/
mise run build   # site into dist/
```

## Definition of done

`mise run check` is green, new logic has a direct test, and the change is on `main`.
