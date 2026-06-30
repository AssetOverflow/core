# Audio Section — Pipeline Overview & Primer

A from-the-ground-up reference for CORE's audio modality: how a waveform becomes
a lawful Cl(4,1) versor, what every spec means, and exactly where (and why)
learned models like Whisper are — and are **not** — involved.

**Audience:** anyone re-familiarising with audio/DSP or onboarding to the audio
section. No one knows everything; this is the single greppable source of truth.

**Authoritative sources this summarises** (read these for the binding contract):
- [`docs/decisions/ADR-0181-audio-compiler-delta-crdt.md`](decisions/ADR-0181-audio-compiler-delta-crdt.md) — the decision.
- [`docs/plans/audio-compiler-spec.md`](plans/audio-compiler-spec.md) — the compiler spec.
- [`docs/plans/audio-compiler-eval-plan.md`](plans/audio-compiler-eval-plan.md) — eval gates + teacher policy.
- Code: `sensorium/audio/{canonical,frames,lexer,parser,operators,compiler,checksum,arena,teachers}.py`.

> All numbers below are pulled from the code as of the ADR-0181 PR-2…PR-6 stack
> (merged to `main`). If you change a constant, update this doc in the same PR.

---

## 0. The one big idea

Most systems turn audio into an **embedding** (an opaque vector from a neural
net). CORE refuses that. It treats audio like a **compiler treats source code**:
raw waveform → measured acoustic facts → a *typed intermediate representation
(IR)* → a lawful geometric object (a 32-dim Cl(4,1) versor). Every step is
deterministic and checksummed, so the same bytes always produce the same result,
bit-for-bit. Learned models may only *annotate*, never *define*.

```mermaid
flowchart LR
    W[waveform] --> C[canonicalize<br/>mono 24kHz f32]
    C --> F[frame grid<br/>20ms / 10ms]
    F --> L[acoustic lexer<br/>energy / voicing / pitch]
    L --> P[parser → typed AudioIR<br/>speech / pause / prosody / turn]
    P --> O[operators → rotors]
    O --> V[(32,) versor<br/>SUBSTRATE]
    W -. optional .-> T[Whisper / NeMo<br/>transcript]
    T -. typed label .-> P
    P -.-> AN[content.* anchors<br/>EVIDENCE — never touches versor]
```

---

## 1. Audio file fundamentals (the refresher)

A digital audio file is just **amplitude samples over time**. The specs that
define one:

| Property | What it means | CORE's canonical choice |
|---|---|---|
| **Sample rate** | samples per second (Hz) | **24,000 Hz** (`CANONICAL_SAMPLE_RATE`) |
| **Channels** | mono (1), stereo (2), … | **mono** (multi-channel is averaged down) |
| **Sample format / bit depth** | how each sample is stored (int16, float32…) | **float32**, range ~[−1, 1] |
| **Encoding** | PCM (raw) vs compressed (MP3/AAC) | PCM-equivalent float array |

- **Nyquist limit:** a 24 kHz sample rate represents frequencies up to **12 kHz**
  (half the rate). Speech energy is mostly below 8 kHz, so 24 kHz comfortably
  captures speech + sibilance. (Teacher ASR gets a *derived* 16 kHz stream
  because models like Whisper expect 16 kHz.)
- **Why no `.wav` files in the repo:** tests synthesize signals from parameter
  specs (`evals/audio_sensorium/fixtures.json`) instead of committing binary
  blobs. A spec like `{tone, 150 Hz, 300 ms}` is diffable and greppable; a `.wav`
  is opaque. The signal is a pure function of the spec, so "what's pinned is
  exactly what's tested." `numpy` `PCG64` RNG + cast-to-float32-at-the-boundary
  makes it bit-reproducible across machines.

---

## 2. Stage 1 — Canonicalize (`canonical.py`)

Turns *whatever arrived* into the one canonical form everything else assumes:

1. **Downmix to mono** — average across channels (handles `(N,)`, `(N,C)`,
   `(C,N)`; channel axis = the smaller dimension).
2. **Resample to 24 kHz if needed** — using a **pinned polyphase FIR filter**
   from the pack (not an ad-hoc resampler — determinism). Same-rate input is an
   exact passthrough.
3. **Hash twice for provenance:**
   - `source_sha256` = hash of the original bytes as received.
   - `canonical_sha256` = hash of the canonical float32 image.

Output is an `AudioSignal` (samples + sample_rate + start/end ms + the two
hashes). **No raw PCM travels further than this** in the trace — only hashes.

> *FIR = Finite Impulse Response filter; polyphase = an efficient way to resample
> by rational ratios. "Pinned" = the exact filter taps are frozen pack data so
> resampling is byte-identical everywhere.*

---

## 3. Stage 2 — Frame grid (`frames.py`)

Audio is non-stationary (it changes constantly), so we analyse it in short
overlapping chunks called **frames**:

- **Window = 20 ms** (`FRAME_MS`) → 480 samples at 24 kHz.
- **Hop = 10 ms** (`HOP_MS`) → 240 samples → **50% overlap** between frames.
- The last partial frame is **zero-padded** to a full window, so the grid is a
  pure function of (length, rate, frame_ms, hop_ms).

A "hop" is the time unit the rest of the pipeline counts in: **hop index `i` =
the chunk starting at `i × 10 ms`.** So 300 ms of audio ≈ 30 hops.

---

## 4. Stage 3 — Acoustic lexer (`lexer.py`) — *the actual audio features*

This is where DSP happens. For **each frame** it measures facts and
**quantizes** them (so the token stream hashes deterministically — "quantize
before semantics"). Per hop it emits one primary classification token plus
descriptors:

### 4a. Energy (loudness)
`log_energy_db = 20·log10(RMS)` — RMS is root-mean-square amplitude. Quantized to
**1 dB integer bins**. Frames quieter than **−55 dB** (`SILENCE_DB`) → `silence`.

### 4b. Voicing — voiced vs unvoiced
Uses **Zero-Crossing Rate (ZCR)** = fraction of adjacent samples where the signal
flips sign. Vowels (voiced) are quasi-periodic → **low ZCR**; fricatives/noise →
**high ZCR**.
- `voiced` if `ZCR ≤ 0.20` (`VOICED_ZCR_MAX`) **and** `dB ≥ −45` (`VOICED_MIN_DB`).
- Otherwise (loud but noisy) → `unvoiced`, and it records a **spectral centroid
  bin** (16 bins) = the "center of mass" of the spectrum (bright vs dull), from a
  Hanning-windowed FFT.

### 4c. Pitch (F0) — only for voiced frames
Estimates **fundamental frequency** via **autocorrelation** (pYIN-style: find the
lag where the signal best correlates with a delayed copy of itself; that lag =
the pitch period).
- Search range **50–500 Hz** (`F0_MIN/MAX_HZ`) — the human voice range.
- Pitch in **cents**, not Hz: `cents = 1200·log2(Hz / 55)`, referenced to **55 Hz
  (note A1)**, quantized to **25-cent bins**. Cents are a log scale — equal
  *musical* intervals are equal cent-distances, which is how prosody works
  perceptually.
- Keeps the **top 2 candidates** as `(cents_q, prob_q)` pairs, `prob_q` ∈ 0–255
  = peak strength/confidence.

> Net: each hop becomes integer tokens like `energy_bin(−9)`, `voiced(dB, zcr)`,
> `pitch_candidates(cents_q, prob_q, …)`.

---

## 5. Stage 4 — Parser → typed AudioIR (`parser.py`)

Collapses runs of like frames into **typed spans/events** (never per-frame
noise). Six event families:

| Family | Built from | Example event types |
|---|---|---|
| **speech_spans** | runs of `voiced` | `speech.voiced` |
| **pause_spans** | runs of `silence` | `pause.short`, `pause.long` (≥ **30 hops = 300 ms**) |
| **prosody_arcs** | F0 slope / energy delta over a voiced span | `prosody.rise`, `prosody.fall`, `prosody.emphasis` (≥ **6 dB** swing) |
| **turn_events** | a long pause | `turn.boundary` |
| **non_speech_events** | runs of `unvoiced` | `nonspeech.noise` |
| **content_anchors** | **teacher hints only** (PR-6) | `content.transcript`, … |

Prosody logic: compare F0 at the end vs start of a voiced span — rising ≥ 1
cent-bin → `prosody.rise` (question-like), falling → `prosody.fall`
(statement-like). The whole IR is hashed → `ir_sha256`.

---

## 6. Stage 5 — Operators → rotors → versor (`operators.py`, `compiler.py`)

Each event type maps to a **declared rotor** (a rotation in the geometric
algebra), not an opaque vector:

- v1 uses **elliptic bivector rotors only** — 6 planes in Cl(4,1) (blade indices
  6,7,8,10,11,13) that square to −1, giving the well-behaved
  `R = cos(θ/2) + B·sin(θ/2)`. This guarantees the composition is always a **unit
  versor** (`versor_condition < 1e-6` without weakening the threshold).
- The angle `θ_q` is an **integer** = `base_theta_q + Σ(gain × quantized_attr)`,
  clipped. E.g. `prosody.rise` (plane 10, base 64) adds `3 × slope_q`.
  `THETA_STEP = π/512` (1024 steps span the circle).
- `compile_events` folds the canonically-ordered events into one versor by
  repeated geometric product + unitize. **Events with no operator (like
  `content.*` teacher hints) are skipped** — that's why teachers can't change the
  versor.
- Result = a **(32,) float32 multivector** — the single object that crosses into
  CORE's field/vault, exactly like a text token does.

The operator table (the `B_*` aliases) is the audio "phonology": `B_PAUSE_LONG`,
`B_SPEECH`, `B_PITCH_RISE`, `B_PITCH_FALL`, `B_EMPHASIS`, `B_TURN`, `B_NOISE`.

---

## 7. The checksum chain & merge key (`checksum.py`)

Every link is content-addressed:

```text
source_sha256 → canonical_sha256 → token_stream_sha256 → ir_sha256
              → pack_manifest_sha256 → projection_sha256
```

The **merge key = `(canonical_sha256, ir_sha256, projection_sha256)`** — what the
Delta-CRDT (`arena.py`, PR-5) uses to dedup/order. Teacher hints move only the
`ir_sha256` leg (evidence), never `projection_sha256` (substrate).

---

## 8. Concurrency — the Delta-CRDT arena (`arena.py`, PR-5)

Each compiled chunk is one `AudioCompilationUnit` (the delta). Units accumulate
in a thread-local, share-nothing `AudioArena`; the merge kernel folds arena
snapshots into one **content-addressed, deduplicated, totally-ordered** set keyed
by `merge_key`. The merge is permutation- and duplicate-invariant, so
`hash(Sequential_Ingest) == hash(Concurrent_CRDT_Ingest)` — the proof obligation
of [ADR-0180](decisions/ADR-0180-crdt-sharded-vault-concurrency.md). The Python
layer mirrors the Rust `LocalArena`/`SemilatticeDelta`/`merge_kernel`
(`core-rs/src/vault.rs`) so they stay in parity when the binding lands.

---

## 9. Where learned models fit — and where they emphatically do not

This is the most-asked question, so it gets its own section.

### Three things a model *could* hand you

| What | Used in CORE? | Where it comes from |
|---|---|---|
| **Embeddings** (opaque latent vectors) | ❌ **Never** — explicitly rejected | the whole "no embedding bridge" rejection (CLAP/EnCodec as substrate) |
| **Audio specs** (pitch, energy, voicing, pauses, prosody, turns) | ✅ Yes | **CORE's own deterministic DSP compiler** (`lexer.py`/`parser.py`) — *not any learned model* |
| **Text transcript** (the words) | ✅ (intended, as evidence) | **Whisper / NeMo** — admitted as a typed *label* |

### Concretely

- **The audio specs do NOT come from Whisper.** Every acoustic fact — framing,
  energy, ZCR voicing, F0/pitch, spectral centroid, pause/turn detection — is
  measured by CORE's own lawful DSP. Whisper has zero involvement. That's the
  native substrate, and it stands alone.
- **Whisper's only intended job is audio → words.** It would emit a **text
  transcript** (+ timestamps/language ID), attached to a time span as a
  `content.transcript` anchor — a **lexical label / evidence** in the IR. It fills
  the one gap DSP can't: *what words were said*, vs *how they were said*.
- **We take Whisper's discrete text output, never its internals.** Whisper is
  itself a neural net full of embeddings — but CORE ingests only its **emitted
  string + timestamps** (a typed, checksummed hint), never its latent vectors. A
  word like `"home"` as a label, not a 768-dim vector.
- **CLAP is the one to watch.** Its natural output *is* embeddings + audio-text
  alignment. The eval plan admits CLAP only for **coarse text labels**
  ("laughter", "alarm") and rejects its embeddings. The rule across all teachers:
  **words/labels in, vectors never.**

### The two lanes never mix

```text
waveform ─┬─► CORE DSP compiler ──► AudioIR specs (pitch/energy/pauses/turns) ──► versor   [SUBSTRATE]
          │
          └─► Whisper ──► "are you coming home?" + timestamps ──► content.transcript label  [EVIDENCE]
                                                                  (never touches the versor)
```

### Teacher policy, verbatim (eval-plan §4)

```text
Use teachers to label or align.
Never let teachers define the substrate.
Never fold teacher embeddings directly into the main versor path.
Only admit teacher outputs through typed, versioned, checksumed hints.
```

### Current status (important)

As of the merged PR-6: the teacher lanes are **declared, gated behind optional
extras, and inert.** `load_teacher("whisper")` raises `TeacherUnavailable` —
**no real model is wired or imported.** The only working teacher is the
deterministic `StubTranscriptTeacher` (no weights), used to prove the contract.
The structural guarantee — a teacher hint leaves the versor/`projection_sha256`
**byte-identical** — is enforced by a failable test
(`tests/test_audio_teachers.py::test_teacher_hint_does_not_change_versor`).

The real doctrinal commitment is **not** admitting a teacher; it's whenever
someone builds the **consumer** that reads teacher hints into comprehension. No
such consumer exists yet. That is the PR to scrutinise hard.

### Teacher = bootstrap scaffolding; the serving path stays Whisper-free

A teacher is **scaffolding for the teaching phase, not a production component.**
This is *not* ML distillation: CORE has no weights, so Whisper does not train a
"student." Its only job is to *propose* transcripts → a human reviews them → they
become **taught associations** (acoustic-pattern ↔ lexeme) in curated packs. Then
the engine decodes audio and recalls against what it learned — and Whisper is
gone.

**Serving rule:** the production/serving path must never call a teacher. Teachers
are admitted only on the *teaching* side (reviewed, evidence-only). The day
someone proposes a teacher in the serving path is the day to say no.

**Production is Whisper-free — on one condition.** Removing the teacher only
leaves the engine able to handle words if, by then, a **lawful runtime path**
carries what the teacher bootstrapped. Two ways that holds:

- **(A) Words arrive as text** — audio stays a paralinguistic sense
  (prosody/turns/affect/coarse phonetics); the *what* comes through the text
  modality. Whisper never needed at runtime. Cleanest.
- **(B) The deterministic audio→lexeme decode matured** — a formant/phonetic
  front-end + taught vocabulary lets the engine recognise words itself, lawfully,
  0-param. Whisper was just the bootstrap that helped build that vocabulary.

Paths (A)/(B) are the subject of
[ADR-0183 (stub)](decisions/ADR-0183-lawful-audio-lexeme-path.md) — deferred, but
on the record so the serving-path boundary isn't crossed silently.

**The trap to avoid:** teaching with a model does **not** automatically transfer
word-recognition into a 0-param engine the way distillation transfers into a
student network. Nothing transfers unless path (A) or (B) actually exists to use
what was taught. Remove the teacher with neither in place and the engine is
simply **deaf to words again** — it keeps all of prosody/turns/affect, but loses
lexical content.

Hold it in one line: **the teacher teaches; the lawful path serves.**

---

## 10. Specs quick-reference (all from the code)

| Spec | Value | Source |
|---|---|---|
| Canonical sample rate | 24,000 Hz (Nyquist 12 kHz) | `canonical.py` |
| Format | mono float32 | `canonical.py` |
| Frame / hop | 20 ms (480 smp) / 10 ms (240 smp), 50% overlap | `frames.py` |
| Silence threshold | −55 dB | `lexer.py` |
| Voiced criteria | ZCR ≤ 0.20 and dB ≥ −45 | `lexer.py` |
| F0 range / ref / bin | 50–500 Hz / 55 Hz (A1) / 25 cents | `lexer.py` |
| Spectral centroid bins | 16 | `lexer.py` |
| Long pause / turn | ≥ 30 hops (300 ms) | `parser.py` |
| Emphasis threshold | ≥ 6 dB intra-span swing | `parser.py` |
| Rotor type | elliptic bivector, 6 planes (6,7,8,10,11,13) | `operators.py` |
| θ resolution | π/512 per step, 1024 steps | `operators.py` |
| Output | (32,) float32, `versor_condition < 1e-6` | `compiler.py` |
| Merge key | `(canonical_sha256, ir_sha256, projection_sha256)` | `checksum.py` |

---

## 11. The test fixtures, acoustically (`evals/audio_sensorium/`)

Signals are synthesized from `fixtures.json` (no `.wav` blobs). Three primitives:
`_tone` (sine + optional linear F0 sweep), `_silence` (zeros), `_noise` (seeded
Gaussian) — all 24 kHz mono float32.

| Fixture | Synthesis | What the lexer/parser extracts |
|---|---|---|
| `silence_500ms` | 500 ms zeros | 50 hops `silence` → `pause.long` + `turn.boundary` |
| `rise_question` | 300 ms sine, 150 Hz **sweeping +90 → 240 Hz**, amp 0.5 | low ZCR + loud → `speech.voiced`; rising F0 → `prosody.rise` |
| `fall_statement` | 300 ms sine, 230 Hz **sweeping −90 → 140 Hz**, amp 0.5 | `speech.voiced` + `prosody.fall` |
| `noise_burst` | 300 ms Gaussian noise (seed 7, amp 0.3) | high ZCR → `unvoiced` → `nonspeech.noise` |
| `speech_then_pause` | 300 ms 150 Hz tone + 400 ms silence | `speech.voiced` then `pause.long` + `turn.boundary` |

A 0.5-amplitude sine has RMS ≈ 0.354 → ≈ **−9 dB** (well above −45) and very low
ZCR → reliably "voiced." Gaussian noise crosses zero constantly → high ZCR →
"unvoiced." The fixtures are designed so the parser's *accuracy* is checkable,
not just its determinism.

### What the tests actually assert

`tests/test_audio_*.py` (in the PR smoke gate): exact `(32,)` float32 shape;
`versor_condition < 1e-6`; bit-identical replay; frozen `canonical_sha256` /
`ir_sha256` pins; IR-replay equality; **parser accuracy** (`event_type_counts`
match the designed parse); cross-platform versor stability within `atol=1e-6`;
trace hygiene (no PCM); gate-closure; sequential==concurrent merge; and
teacher-shadow invariance. They prove the path is **deterministic, replayable,
checksummed, lawfully shaped, and parses the intended structure** — they do *not*
test real-world speech, accents, noise robustness, or transcription accuracy
(that needs real corpora + the deferred teacher adapters).

---

## 12. Mini-glossary

**PCM** — raw uncompressed samples. **RMS** — root-mean-square amplitude
(loudness). **dB** — log loudness scale. **ZCR** — zero-crossing rate (voicing
proxy). **F0 / pitch** — fundamental frequency. **cents** — log pitch unit (100
cents = 1 semitone). **spectral centroid** — frequency "center of mass"
(brightness). **Nyquist** — max representable freq = ½ sample rate. **frame/hop**
— short analysis window / step between windows. **rotor/versor** — geometric-
algebra rotation operator / the unit object it produces. **FIR** — finite impulse
response (resampling) filter. **Delta-CRDT** — conflict-free replicated data type;
order-invariant merge.

---

## 13. Where to go next

- Run the audio tests: `core test -- tests/test_audio_*.py -q` (or plain
  `uv run pytest tests/test_audio_*.py -q`).
- Compiler internals & rationale: [`docs/plans/audio-compiler-spec.md`](plans/audio-compiler-spec.md).
- Eval gates & teacher policy: [`docs/plans/audio-compiler-eval-plan.md`](plans/audio-compiler-eval-plan.md).
- The decision & trade-offs: [`docs/decisions/ADR-0181-audio-compiler-delta-crdt.md`](decisions/ADR-0181-audio-compiler-delta-crdt.md).
- The concurrency substrate: [`docs/decisions/ADR-0180-crdt-sharded-vault-concurrency.md`](decisions/ADR-0180-crdt-sharded-vault-concurrency.md).
