# Purpose and research questions: Mimir III (draft for the hub's docs/purpose.md)

Draft by Mimir lane 1, for Peter to review; the controller ports it to the hub after review.

**ID note.** The brief names the questions "M Q1" to "M Q3", but `M Q1.1` is already used by Midgard
III in the hub table. This draft writes them "Mi Q1" to "Mi Q3"; rename if Peter prefers another
prefix.

## Mimir III (side branch)

**Purpose Mi1.** Be the circuit knowledge base of Yggdrasil III: hold the characteristics of
designs (structure, Hutton-style statistics, Rent's rule), the provenance relationships of ADR D14,
and the outcomes (quality of result per placer family), in one tidy table. Over time the data
classifies circuits, and the characteristics that classify them are what Mimir is for. Serves area,
speed and power through understanding: a classification says which kind of circuit a design is and
therefore what to expect from a flow.

**Purpose Mi2.** Make every number in the table traceable and checkable: each metric has a
registered definition, a unit, a level, a source and a validation, and each measurer is checked
against constructions with known answers (and against published values where the source can be read)
before its values are trusted.

| Question | Measure | Experiments and features |
|---|---|---|
| Mi Q1 Which characteristics classify circuits? | area, speed | the schema, the measurers and the classification lanes |
| Mi Q1.1 Is each measurer correct: does it give the known answer on constructions with known structure, and the published value where one is readable? | correctness | `tests/test_hutton.py`, `tests/test_rent.py`, the validation table of lane 1 |
| Mi Q1.2 How complete is the coverage: for each design and each level (hdl, elab, gate, lut, ble, clb, placed, routed), which metrics exist? | coverage | `mimir coverage`; MCNC, the Norns netlists and the Loki corpora at the gate and LUT levels in lane 1 |
| Mi Q1.3 Is the import complete: does every row of the existing Norns, Loki and atlas data that carries a number reach the table, and is every skip explained? | completeness | `mimir import`, the per-source counts |
| Mi Q1.4 Is Rent's exponent repeatable (across partitioner seeds, and across fit ranges) so that it can be a classifying characteristic? | correctness | test-retest in lane 1; fit-range study in a later lane |
| Mi Q1.5 Do the structural characteristics (depth, edge length, fanout, reconvergence, Rent p) separate the design families we hold (MCNC, VTR designs, Norns synthetic families, Loki micros)? | area, speed | classification lane (not lane 1) |
| Mi Q1.6 Are the characteristics stable from the gate to the LUT level of the same design, or does mapping change the class? | area, speed | lane 1 holds both levels for the Loki corpora; analysis in a later lane |
| Mi Q2 Do those characteristics predict QoR and placer sensitivity, across placer families? | area, speed | later lane over the imported Norns outcomes |
| Mi Q2.1 Do the characteristics predict routed wirelength, channel width and critical-path delay, for the analytic family and for the annealing family separately? | area, speed | Norns rounds 1-7 rows, labelled by family |
| Mi Q2.2 Do they predict how much a design gains or loses when the placer changes (analytic against annealing, and between placers inside a family)? | area, speed | Norns placer-families experiments |
| Mi Q3 Can synthetic circuits match a Mimir profile? This follows the generator line of Hutton and of Kundarewich and Rose. | area, speed | generator lane (not lane 1) |
| Mi Q3.1 Can a generator reproduce the profile of a real design, to within the measurers' own repeatability? | correctness | Hutton et al. (DAC 1996, FPGA 1997), Kundarewich and Rose (TCAD 2004), Stroobandt et al. (TCAD 2000) |
| Mi Q3.2 Does a profile-matched synthetic circuit give the same QoR and the same placer response as the real design? | area, speed | later lane |

## Measures used by lane 1

Lane 1 answers Mi Q1.1 to Mi Q1.4 only: the correctness of the measurers, the coverage, the import
completeness and the repeatability of the Rent exponent. The Hutton-style definitions in lane 1
are Mimir's own (the sources were unreadable to the lane), so Mi Q1.1 is answered against
constructions with known answers and not against published values.

## Citations

Hutton et al. (DAC 1996, doi 10.1145/240518.240537; FPGA 1997, doi 10.1145/258305.258333),
Kundarewich and Rose (TCAD 2004, doi 10.1109/TCAD.2004.828132), Stroobandt et al. (TCAD 2000,
doi 10.1109/43.863641), Landman and Russo (IEEE Trans. Computers 1971, doi 10.1109/T-C.1971.223159).
Each is verified against its DOI record in `citations.toml`; none was read in full.
