---
name: Verify and release a language
about: Promote a language from `experimental` to `released` by testing it on a real-world project.
title: "lang: verify and release <language> (<project>)"
labels: ["enhancement", "showcase", "good first issue"]
---

This issue covers promoting a language from `experimental` to
`released`. It is a follow-up to a merged *Add a language* issue and
PR; do not open it for languages that have not yet shipped at the
`experimental` tier.

> **Open to any contributor.** You do not need to be the person who
> shipped the language's `experimental` PR — anyone can pick this up.
> If the original language contributor used the tip in the *Add a
> language* sanity-check step, they may already have a fork ready and
> may want to claim this; if you are not them, comment here before
> starting work to avoid duplicate effort.

> **One showcase per contributor.** Like *Add a language*, this is a
> well-scoped first contribution and we keep it open for newcomers. If
> you have already had a showcase PR merged, please do not open
> another one.

The work has two parts, in order:

1. A PR to [`shamefile-showcase`](https://github.com/BKDDFS/shamefile-showcase)
   adding the generated `shamefile.yaml` and a short metadata README
   for this language.
2. A PR to this repo moving the language from the README's
   *Experimental tokens* table into *Supported tokens*, with a link to
   the merged showcase entry.

The showcase repo stores **only `shamefile.yaml` files and metadata** —
no source code. The upstream project URL and commit SHA are recorded so
anyone can clone the original codebase for full context.

## Target

- Language:
- Original language issue / PR:
- Upstream project (URL):
- Upstream project commit SHA:

## Pre-flight checks

- [ ] The language is already merged in this repo at the `experimental`
  tier (row exists in the README's *Experimental tokens* table).
- [ ] The chosen upstream project is actively maintained, has a
  recognizable footprint (popular framework, library, or application
  in this language), and is not a niche or abandoned repo.
- [ ] No other showcase issue or PR is already in flight for this
  language (search both this repo and
  [`shamefile-showcase`](https://github.com/BKDDFS/shamefile-showcase)
  before starting).

## Generate the showcase

- [ ] Clone the upstream project at a specific commit SHA — record it
  above:
  ```sh
  git clone https://github.com/<org>/<repo> /tmp/showcase
  cd /tmp/showcase && git checkout <sha>
  ```
- [ ] Install the latest released `shamefile` and run `shame me .` to
  generate `shamefile.yaml`.
- [ ] Fill the `why` field for every entry. AI assistance is acceptable,
  but add a note to README about that.
- [ ] Run `shame me . --dry-run` and confirm it exits zero (every entry
  has a `why`, no drift between code and registry).

## Showcase PR ([`shamefile-showcase`](https://github.com/BKDDFS/shamefile-showcase))

Open a PR to
[`shamefile-showcase`](https://github.com/BKDDFS/shamefile-showcase)
following its `CONTRIBUTING.md`. The PR adds a directory under the
language name with two files:

```
<language>/<project>/
├── shamefile.yaml
└── README.md
```

The `README.md` must contain:

- [ ] Upstream project URL
- [ ] Commit SHA used for the scan
- [ ] Suppression count
- [ ] Link back to this issue
- [ ] If AI was used to generate `why` fields

> **Do not open a PR to the upstream project** introducing
> `shamefile.yaml` to their repo. If you think a project would benefit
> from shamefile, open an issue (or discussion) in **their** tracker first asking
> whether they want it. Unsolicited PRs are noise for maintainers.

## Promotion PR (this repo)

Open this PR only after the showcase PR is merged.

- [ ] Remove the language row from the README's *Experimental* table.
- [ ] Add token rows to the *Supported tokens* table. The
  *Experimental* table only lists the language name — *Supported tokens*
  requires one row per token with `Token`, `Tool`, and `Language`
  columns, matching the format of existing entries (e.g. Python, JS).
  Find the full list of tokens for this language in
  [`src/languages.rs`](../blob/main/src/languages.rs) under the
  `LANGUAGES` array — each token has a trailing comment naming the
  tool it comes from.
- [ ] Add a link to the merged showcase entry next to the new
  *Supported tokens* rows (footnote, separate column, or short note —
  match whatever convention the README has when this PR is opened).
- [ ] Link this PR with `Closes #<this-issue>`.

## Notes

(anomalies in the showcase run, anything maintainers should know)
