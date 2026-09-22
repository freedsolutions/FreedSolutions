# TypeSafe (Jev) integration

Jev is TypeSafe's "System One" model. It returns **typed, calibrated decisions**
instead of text: you hand it state plus a map of questions, and it answers all of
them in one parallel pass. There is no string to parse and no schema to validate.

## The contract

Taken from the installed SDK (`typesafe_sdk` 0.7.1), not from third-party docs.

| | |
|---|---|
| Base URL | `https://api.typesafe.ai` |
| Path | `POST /v1/systemone` |
| Auth | `Authorization: Bearer <key>` |
| Env var | `TYPESAFE_API_KEY` |
| Model | `jev-latest` |
| Install | `pip install typesafe-sdk` |

> **Do not send the key anywhere else.** Several high-ranking third-party "Jev
> API" pages instruct you to export your `TYPESAFE_API_KEY` and POST it to an
> unrelated host. That is not the vendor endpoint. The SDK's own default is
> `api.typesafe.ai`.

### Three question primitives

| Primitive | Ask | Answer fields |
|---|---|---|
| `Choice` | pick one of up to 255 labels | `.choice`, `.confidence`, `.probabilities{label: p}` |
| `Noul` | yes/no as a probability | `.noul` (0-1) — **no confidence field** |
| `Score` | rate against an ordered rubric | `.score` (may fall between levels), `.confidence`, `.legend`, `.probabilities{level: p}` |

`Noul` returning no confidence is the one real gotcha: the probability *is* the
answer, and its distance from 0.5 is the only uncertainty signal you get.

## The key

```bash
mkdir -p "$HOME/.secrets" && printf 'TYPESAFE_API_KEY=%s\n' "PASTE_KEY_HERE" > "$HOME/.secrets/typesafe.env"
```

Kept outside the repo so it cannot be committed. `jev.load_api_key()` reads the
environment first, then that file.

## Verify

```bash
python ops/typesafe/probe.py
```

Proves the key resolves, auth works, and both a `Choice` and a `Noul` come back
inside their declared types.

## Where Jev is allowed to sit

Jev **advises; it never decides and never writes.** The standing pattern:

1. Deterministic gates run first, in code. A candidate a gate kills is never
   shown to Jev.
2. Jev scores only what survives — the judgment calls a human would otherwise
   eyeball.
3. The confidence cut between AUTO and REVIEW is a **threshold, and thresholds
   are ruled, never inferred**. Backtest, show the calibration curve, let the
   owner pick the number.

Anything Jev proposes still lands in a review file for approval.
