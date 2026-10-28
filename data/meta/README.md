# Mimir MCNC design meta: vocabulary and coverage

Purpose (Peter 2026-10-27): per-design meta information (intent, origin, lineage) as ground-truth label input for E4 and as provenance. Question: Mi Q1. Data file: `mcnc.toml`. Sources: `mcnc-sources.md`. Research output, first in git with the originals pass (2026-10-27).

## Controlled vocabulary

### conf (confidence of one fact)
- `primary`: the benchmark's own documentation or distribution: the MCNC user guide (Yang 1991), the LGSynth89 text, files and comments inside the LGSynth91 distribution archive, the VTR benchmark README. Also the original ISCAS89 notes.
- `secondary`: a later paper or thesis describing the set (here only Hutton 1997 Table 4.2, and Marquardt/Betz/Rose for the flow).
- `inferred`: derived by the lane from the netlist, a name, or an I/O-count match. Never to be used as a sourced fact.
- `missing`: searched for, not found. A valid answer.

### function_class (one value per circuit)
- `arith`: arithmetic/ALU datapath (adders, ALUs, multipliers).
- `control`: bus interfaces, bus controllers, sequencing logic.
- `crypto`: encryption/key schedule circuits.
- `dsp`: filters and numeric iterative solvers (signal-processing style datapath).
- `cpu`: processor-like circuits (program counter, instruction stream, interrupts).
- `fsm`: a finite state machine specified as a state table.
- `pla_random`: two-level PLA or random logic with no stated function. Assigned only from the benchmark category, so conf is `inferred`.
- `unknown`: function not stated in any source found.

Rule used for `function_class_conf`: when the class maps directly from a sourced intent text (for example guide "ALU" to `arith`, "Encription" to `crypto`), the class takes the intent's conf. The mapping itself is the lane's, so when the intent comes from a workshop document and the class is the lane's reading of it (diffeq), the class is `inferred`. A class derived from an inferred intent is `inferred`.

### Other fields
- `original_header`: the circuit's own header comment or first lines, verbatim (leading and trailing blanks stripped), at most 5 lines, never a whole file. Source gives member path and line numbers in the original archive.
- `stated_counts`: input, output, latch, product-term and state counts as the original file or its header states them (PLA `.i .o .p`, KISS2 `.s`, `## inputs/outputs/latches` comments). Not written when the file states none.
- `lgsynth93`: the files of the LGSynth93 (IWLS'93 v4.0) release for the circuit, with the EDIF author/program/timestamp and the e2fmt BLIF date stated in them.
- `licence`, `licence_source`, `licence_notice`, `licence_rule` (all designs, from `licences.toml`; every design matches exactly one rule, an unmatched design fails the import): the benchmark's licence as it states it, never changed or inferred; `none-stated` means the original files and documents carry none and the distribution statements they do carry are quoted in `licence_notice`; a scope question is an "Open question" there, never a conclusion. `licence_source` is the cited file and lines. A primary or secondary licence row from another source is kept.
- `year`: earliest year found in a listing of the circuit. It is NOT the design year. For the four Stanford HL circuits it is 1990 (the HLS Stanford suite list as of 1990-07-20); their SLIF files are dated 1991-01-04.
- `author`, `institution`: original designer. The MCNC distribution names no per-circuit designers. For the ISCAS89 circuits the authors of the ISCAS'89 paper that presents the set (Brglez, Bryan, Kozminski, MCNC) are recorded, always `inferred`: the paper (p.1929) says the benchmarks were assembled from industrial and university sources and names no designer. s38417 and s38584.1 are listed in its Table 1; for s298 the FSM version is not shown to be the ISCAS89 netlist. For the four Stanford HL circuits the institution is Stanford (Olympus; set provided by Giovanni De Micheli) and the author stays `missing`, except tseng ("Example from Tseng").
- `lineage`: ordered steps. A step with `conf = "missing"` is a known gap (a conversion that the sources do not document). `lineage_gaps` counts them. `lineage_conf` covers the sourced steps only, so read it together with `lineage_gaps`.

## Coverage table (20 circuits x 13 fields)

| circuit | suite | original_file | original_format | intent | function_class | author | institution | year | lineage | original_header | stated_counts | lgsynth93 | licence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| alu4 | found(P) | found(P) | found(P) | found(P) | found(P) | missing | missing | found(P) | found(P) | found(P) | found(P) | found(P) | found(P) |
| apex2 | found(P) | found(P) | found(P) | missing | inferred | missing | missing | found(P) | found(S) | found(P) | found(P) | found(P) | found(P) |
| apex4 | found(P) | found(P) | found(P) | missing | inferred | missing | missing | found(P) | found(S) | found(P) | found(P) | found(P) | found(P) |
| bigkey | found(P) | found(P) | found(P) | found(P) | found(P) | missing | missing | found(P) | found(P) | found(P) | found(P) | found(P) | found(P) |
| clma | found(P) | found(P) | found(P) | found(P) | found(P) | missing | missing | found(P) | found(P) | found(P) | found(P) | found(P) | found(P) |
| des | found(P) | found(P) | found(P) | found(P) | found(P) | missing | missing | found(P) | found(P) | found(P) | none | found(P) | found(P) |
| diffeq | found(P) | found(P) | found(P) | found(P) | inferred | missing | found(P) | found(P) | found(S) | found(P) | none | found(P) | found(P) |
| dsip | found(P) | found(P) | found(P) | found(P) | found(P) | missing | missing | found(P) | found(P) | found(P) | found(P) | found(P) | found(P) |
| elliptic | found(P) | found(P) | found(P) | found(P) | found(P) | missing | found(P) | found(P) | found(S) | found(P) | none | found(P) | found(P) |
| ex1010 | found(P) | found(P) | found(P) | missing | inferred | missing | missing | found(P) | found(S) | found(P) | found(P) | found(P) | found(P) |
| ex5p | found(P) | found(P) | found(P) | missing | inferred | missing | missing | found(P) | found(S) | found(P) | found(P) | found(P) | found(P) |
| frisc | found(P) | found(P) | found(P) | found(P) | found(P) | missing | found(P) | found(P) | found(S) | found(P) | none | found(P) | found(P) |
| misex3 | found(P) | found(P) | found(P) | missing | inferred | missing | missing | found(P) | found(S) | found(P) | found(P) | found(P) | found(P) |
| pdc | found(P) | found(P) | found(P) | missing | inferred | missing | missing | found(P) | found(S) | found(P) | found(P) | found(P) | found(P) |
| s298 | found(P) | inferred | inferred | found(S) | found(S) | inferred | inferred | found(P) | inferred | found(P) | found(P) | found(P) | found(P) |
| s38417 | found(P) | found(P) | found(P) | missing | missing | inferred | inferred | found(P) | found(P) | found(P) | none | found(P) | found(P) |
| s38584.1 | found(P) | found(P) | found(P) | missing | missing | inferred | inferred | found(P) | found(P) | found(P) | none | found(P) | found(P) |
| seq | found(P) | found(P) | found(P) | missing | inferred | missing | missing | found(P) | found(S) | found(P) | found(P) | found(P) | found(P) |
| spla | found(P) | found(P) | found(P) | missing | inferred | missing | missing | found(P) | found(S) | found(P) | found(P) | found(P) | found(P) |
| tseng | found(P) | found(P) | found(P) | found(S) | found(S) | found(P) | found(P) | found(P) | found(S) | found(P) | none | found(P) | found(P) |

Legend: found(P) primary source, found(S) secondary source, inferred, missing, none = no row (the field is only written where an original states something). Lineage "found(P)" means the sourced steps are documented; the conversions marked as gaps in `mcnc.toml` are not. Lineage gaps remaining: apex2 1, apex4 1, diffeq 1, elliptic 1, ex1010 1, ex5p 1, frisc 1, misex3 1, pdc 1, s298 1, seq 1, spla 1, tseng 1.

### Totals by field (20 circuits)

| field | found(P) | found(S) | inferred | missing | no row |
|---|---|---|---|---|---|
| suite | 20 | 0 | 0 | 0 | 0 |
| original_file | 19 | 0 | 1 | 0 | 0 |
| original_format | 19 | 0 | 1 | 0 | 0 |
| intent | 8 | 2 | 0 | 10 | 0 |
| function_class | 7 | 2 | 9 | 2 | 0 |
| author | 1 | 0 | 3 | 16 | 0 |
| institution | 4 | 0 | 3 | 13 | 0 |
| year | 20 | 0 | 0 | 0 | 0 |
| lineage | 7 | 12 | 1 | 0 | 0 |
| original_header | 20 | 0 | 0 | 0 | 0 |
| stated_counts | 13 | 0 | 0 | 0 | 7 |
| lgsynth93 | 20 | 0 | 0 | 0 | 0 |
| licence | 20 | 0 | 0 | 0 | 0 |

Originals pass (2026-10-27): intent sourced (P or S) went from 9 to 10 (fix round 1: s38417 and s38584.1 are back to `missing`, the paper says the function is not available and "real-chip based" is only a note), author from 0 to 1 primary (tseng; the ISCAS89 paper authors for s38417 and s38584.1 are `inferred`), institution from 0 to 4 primary (the four Stanford HL circuits; MCNC as the ISCAS89 authors' affiliation is `inferred`), original_file inferred 2 to 1, suite inferred 2 to 0. The two-level circuits and the IWLS93 set carry no descriptions, so their intent, author and institution stay `missing`.

## Notes on specific results
- apex2, apex4, misex3, seq, des: listed already in the Dec 1988 (v2.0) LGSynth89 text. The others appear first in the Jan 1991 (v3.0) guide or in the 1991 archive.
- diffeq, elliptic, frisc, tseng are NOT in the guide tables. They are in the LGSynth91 archive as `slif/hlexamples/*.slif`; its `slif/README` calls the directory "10 SLIF files corresponding to high level benchmarks of the HL synthesis workshop suite". So the brief's "HLS benchmarks" claim is supported for the set, but no source found says which workshop year or who designed each.
- s298: the VTR netlist (3 in, 6 out, 8 latches, 1930 LUT-level nodes) does not match the ISCAS89 s298 (14 flip-flops, 119 gates) that is in the archive `blif/` dir. It fits the KISS2 FSM `s298` (218 states, 8 state bits) instead. This is inferred, not sourced.
- s38584.1: the ".1" is the guide's asterisk footnote: corrected versions of the originals (see `/bench.update`, not retrieved).
- adder and multiclock are in the VTR README name list but not in circuits.txt and are not MCNC LGSynth circuits as far as the sources show. See `mcnc.toml`, both inferred from the netlists.
- README list in VTR has 22 names; circuits.txt has the 20 used here.
- elliptic: the HLSynth91 Stanford list (cbl-wb-hls91-benchdoc) says "Fifth Order Elliptic Filter", which supports the earlier brief wording; Hutton's "elliptic eqn solver" differs and is kept as a secondary note.
- The ten Stanford HL names in the LGSynth91 `slif/hlexamples` directory are the ten of the Stanford HLS suite list (daio_receiver, daio_phase_decoder = phase_decoder, diffeq, ecc, elliptic, frisc, gcd, parker1986, traffic, tseng).
- bigkey: the file header says 224 latches, the guide table says 221 (both recorded).
- ex5p is the LGSynth93 name of ex5.pla: the product-term lines of IWLS93 pla/ex5p.pla equal those of LGSynth91 pla/ex5.pla.
- The sources of the originals are in `mcnc-sources.md`; the originals themselves are private and never committed.
