# Mimir run record: `mimir-run.json` (record_version 1)

Date 2026-10-28. Lane: norns-mimir-runrecords (branch `feat/run-records` in mimirIII and nornsIII).
Extends `2026-10-27-mimir-structures.md` section 4 (the `mimir-run.json` that `mimir.structrun`
writes) and `2026-10-27-mimir-schema-v2.md` sections 3.4, 3.5 and 6 (flow configurations).

## 1. Purpose, questions, measures

Purpose (Peter 2026-10-27, decision 5): a runner writes the full how-obtained data of each run at
run time, so that Mimir imports it as a `full` flow configuration without reconstructing anything.

- **Mi Q2.3:** which parameters change the mapping (every run links to its flow configuration).
- **N Q1.x, N Q2.4:** the Norns placer comparisons need the exact placer parameters of each run.

Measures: the share of new Norns runs imported as `full` (target 100%, or each `partial` run with
the missing parameter named in the report); the number of parameters reconstructed for a new run (0).

## 2. Principles

1. The record is written by the runner, from the run itself: the command it ran, the log the tool
   wrote, the binary and source tree it used. Nothing is reconstructed later.
2. The writer is stdlib only and does not import Mimir. The importer validates the record against
   this spec and refuses one that fails it, with the list of failures.
3. A tool default is a value read from the tool's source at a named version and cited
   `file:line`; a value no source states is `unknown`, never guessed.
4. No absolute path, home path, user name or real host name is written. Paths become placeholders,
   the host becomes its alias.
5. Deterministic: sorted keys, one-space indent, `\n` line ends, UTF-8.

## 3. The record

One JSON object per run, named `mimir-run.json`, in the run's own directory. Top-level keys:

| Key | Type | Meaning |
|---|---|---|
| `record_version` | int | 1 |
| `kind` | str | `norns-run` (the importer accepts only known kinds) |
| `source` | str | the `run.source` label, for example `norns-placers-d4` |
| `design`, `arch` | str | design name; architecture name (no path, no `.xml`) |
| `seed` | int | the run's seed |
| `arm` | str | the arm token; a start temperature is part of it (`ext_nextpnr_sa-t1`) |
| `family` | str | `analytic`, `annealing` or `` (the schema's placer families) |
| `host` | str | host alias `host-<n>` (section 5); there is no other value |
| `kernel` | str | kernel release (no person is identified by it) |
| `started_utc` | str | `YYYY-MM-DDTHH:MM:SSZ` (checked by the importer) |
| `steps` | list | the tool runs in order (3.1) |
| `time_s`, `peak_rss_mib` | number or null | the sum of the step times (steps marked `shared` left out); the largest RSS of the tool steps. `null` when a step did not report it |
| `time_conf` | str | `given`, or `unknown` exactly when `time_s` is null (a time is never recorded as 0) |
| `placer_time_s` | number or null | external-placer arms only: the time of the placer step alone (the last `nextpnr` step, the attempt whose result was used) |
| `ok` | bool | the last step exited 0 |
| `tools` | object | per tool (3.2) |
| `params` | object | `"step.key"` to `{value, conf, source}` (3.3) |
| `inputs`, `artifacts` | object | role to `{path, sha256}` (3.4) |

### 3.1 `steps`
`{name, argv, exit_code, time_s, time_conf, peak_rss_mib, locked, shared}`, and `script_sha256` for a
helper script. `argv` is the exact command line of the tool (without the `flock` and `/usr/bin/time`
wrappers); a path is a placeholder: `<run>/x` under the run directory, `<work>/x`, `<vtr>/x`,
`<norns_vtr>/x`, `<runs>/x`, `<tmp>/x`, a named role such as `<blif>`, `<arch>`, `<vpr>`, `<nextpnr>`,
`<json>`, `<anchors>`, `<placed>` or `<read_flat_place>`, or `<abs>/name` for any other absolute path.
A retried run lists every attempt. The steps of a run: `vpr`, `nextpnr`, and the helper scripts that
make what those two read (`flatplace_chains`, `nextpnr_readback`, `nextpnr_blif2json`). `time_s` of
a tool is its own wall time (`/usr/bin/time -v`, so a wait for the lock is not counted), of a helper
script its wall time; when `/usr/bin/time` printed no value the field is null with `time_conf`
`unknown`. `peak_rss_mib` is the maximum resident set size (null for a helper script, or when not
reported). `locked` is whether the step held the Norns lock. `shared` marks a step run once for
several records of a design (the reference collapse, the converter): it is listed in each record but
left out of the record's `time_s`. A `shared` step that did not run in this process (a resumed sweep) is
not listed.

### 3.2 `tools`
Per tool: `commit` (40-hex HEAD of its source tree, or ``), `commit_how`, `clean` (true, false, or
null when there is no tree; tracked files only; **at record time**), `dirty_diff_sha256` (sha256 of
`git diff HEAD` when not clean, at record time), `binary_sha256`, `binary_version` (the `--version`
text), `built_dirty` (the version text ends its revision in `-dirty`: the binary was built from a dirty
tree; null without a version text), `version_names_commit` (the text contains the first 10 characters
of `commit`, or, for a script run from its tree, the tree is clean), `is_script`, and for a tool built
from a `git archive` copy `build_copy` = `{differs, extra, sha256, unlisted, is_head}`: the tracked
paths whose content differs from HEAD, the files of the copy that HEAD lacks (an overlay), the sha256
of each, the differences that are not listed exemptions, and whether there are none. A listed
exemption is an extra file the build adds, or a tracked file the build patches where the content check
finds only the listed lines added and nothing removed.

The commit is a `given` parameter only when
- for a binary: its `--version` text names HEAD and does not say `-dirty` (built from a clean tree);
- for a tool built from a copy: `build_copy.is_head` (nothing differs but listed, hashed exemptions);
- for a script run from its tree: the tree is clean at record time.

Otherwise the commit parameter is `unknown` (the schema has no `inferred` confidence; the source starts
`inferred at record time` and says why), so the configuration is `partial`. The dirty flag
(`tool.<t>_source_clean`) and the diff hash (`tool.<t>_dirty_diff_sha256`) are their own parameters,
their source labelled "at record time"; `tool.<t>_built_dirty` is the binary's own statement. Each
build-copy difference is a parameter `tool.<t>_build_copy_modified[<path>]` or
`tool.<t>_build_copy_extra[<path>]` (the file's sha256; the source says whether it is a listed
exemption; at most 50 are listed per kind, with a `..._count`).

### 3.3 `params`
Every value is a string. `conf` is one of:

- `given`: a source states the value. The source is `command line`, `vpr.out:<line>` (the tool's
  own echo of the effective option, read from the run's log), or a recorded fact. A `given`
  parameter has a non-empty value (write `(empty)` for an empty one).
- `default`: the tool's default, read from the tool source **as committed** at the recorded commit
  (`git show <commit>:<path>`, never the working tree); the source names the commit (first 8
  characters) and ends in `path:line` or `path:first-last` (for example
  `vtr-tree 3c9a4d23 vpr/src/base/read_options.cpp:2645-2647`).
- `default-unrecorded`: left to the tool default, but the source is not available.
- `unknown`: no source states it.

The importer counts `unknown` and `default-unrecorded` as non-given: a configuration with one is
`partial`, otherwise `full`.

The keys are `step.key`: `run.seed` (the seed; kept out of the configuration hash, so the seeds of
one setup share a configuration), `run.seed_default`, `tool.<tool>_commit`,
`tool.<tool>_source_clean`, `tool.<tool>_built_dirty`, `tool.<tool>_binary_sha256`,
`tool.<tool>_dirty_diff_sha256`, `vpr.<option>` (an option VPR echoed; `vpr.placer_opts.seed` is the
seed it echoes, kept out of the configuration hash like `run.seed`), `vpr.cmd.<flag>` (a flag on the
command line), `vpr.options_echo` (an `unknown` row: the log has no echo header), `nextpnr.cmd.<flag>`,
`nextpnr.vopt.<key>`, `nextpnr.<setting>` (a default), `nextpnr.router` (`none` with `--no-route`),
`inputs.<role>_sha256` and `artifacts.<role>_sha256` (an `unknown` row: the file was absent). A runner
may add keys; the importer takes the part before the first `.` as the step.

VPR echoes its effective options (netlist, analytical placer, router and analysis groups; the
placer group when the annealer runs); an option that VPR neither echoes nor receives on the command
line is not in the record. The echo is a statement of the run itself, so it is `given`. A log
without the echo header makes `vpr.options_echo` `unknown`.

nextpnr settings are **enumerated from the source** at the recorded commit: every
`ctx->setting<T>("name"[, default])` and `*_or_default(ctx->settings, ctx->id("name")[, default])`
in the files the generic flow runs (`command.cc`, `timing*.cc`, the chosen placer, the common placement
code, `generic/pack.cc`, `arch.cc`, `main.cc`, and the overlay files of the build copy). A name given on
the command line is `given`. Any other has its default cited (the literal in the call, the
`if (settings.find(...) == settings.end())` line of `command.cc`, or the helper's default argument
in `util.h`); a name with no literal default is `default-unrecorded`, which makes the configuration
`partial`. With `--no-route` the router does not run and its settings are not read. The router
options of VPR are the ones it echoes.

### 3.4 `inputs`, `artifacts`
`{path, sha256}`: `path` is relative (a placeholder prefix is allowed, never a leading `/` and
never `..`), `sha256` is 64 hex. The role `netlist` is required in `inputs`: its sha256 is the
run's input identity (a record without it is refused). The role `arch` becomes the parameter
`arch.arch_file_sha256`. A file the runner expected but did not find (a failed step's output) is not
dropped: it is an `unknown` parameter `inputs.<role>_sha256` or `artifacts.<role>_sha256`.

## 4. Import (`mimir import-runrecords <db> <dir>`)

Every `mimir-run.json` under `<dir>` is read and checked (section 6). A record that fails is
refused and listed with every reason; the others are imported and the exit code is 1 when any was
refused. For each valid record:

- `flow_config`: name `<source>/<arm>`, text = the step command lines joined by newlines with the
  value after `--seed` replaced by `<seed>`, `text_kind` = `recorded-normalised`, origin
  `mimir-run.json record_version 1`; its parameters are the record's, with the conf as recorded.
  The configuration hash is `Spec.config_hash` (`run.seed` and `vpr.placer_opts.seed` excluded).
  A configuration is stored only when its hash is absent (never replaced). A stored configuration
  with the same hash and another text or text kind (a reconstructed one) refuses the record, with
  the reason `config:` in the report.
- `flow_param`: one row per record parameter, plus `arch.arch_file_sha256`.
- `run`: key `(source, design, arch, seed, arm)`, `tool_commit` = the placer's tool commit (nextpnr
  for an external-placer arm, else VPR, else the first tool by name), `input_sha256` = the netlist
  sha256, `command_line`, `time_s`, `peak_rss_mib` (null when unknown) and `host` from the record,
  `tool_commits` = `tool=commit[-dirty]` pairs for every tool (`-dirty` unless `clean` is true).

Existing reconstructed runs are never changed: the records have their own `source`, and the
time and RSS fill of `import_runs` skips runs whose origin is a record. Importing the same records
again changes nothing. The `--source` filter of the report is an exact source name. A root that is
not a directory is an error.

## 5. Host alias

The alias map is the one of `2026-10-28-mimir-host-alias.md` (TOML table `[hosts]`, lower-cased real
name to `host-<n>`, append-only, `<map>.lock` with `flock`, created only by `mimir host-alias --init`).
The Norns writer follows it exactly: path `$MIMIR_HOST_MAP`, else
`work/mimir-data/remote-private/hosts.toml` of the workspace; a read takes a shared lock when the
lock file exists; an unknown name takes the exclusive lock, re-reads, numbers `host-<max+1>` and
appends one `"name" = "host-n"` line (name as a TOML basic string, a newline added first when the
file lacks its final one). **No map, or a missing file, is an error that names `MIMIR_HOST_MAP`:**
the writer writes no record for that run and the sweep logs it; there is no `host-unmapped`. The real
name is never written to a record.

## 6. Validation (what the importer refuses)

A record is refused when: `record_version` is not 1 or a required key is missing or has the wrong
type; `kind` is unknown; `family` is not a schema family; `host` is not `host-<n>`; `started_utc` is not
`YYYY-MM-DDTHH:MM:SSZ`; `steps` is empty or a step lacks a field or has a wrong type (including
`locked` not a bool and an `argv` item that is not a string); `time_conf` is not `given` or
`unknown`, or `time_s` is null when it is `given` (or a number when `unknown`); a tool commit is not
`` or 40-hex or a `binary_sha256` is not `` or 64-hex; a parameter lacks `value`, `conf` or `source`, has an unknown
`conf`, has an empty `source`, is `given` with an empty value, or is `default` with a source that
does not end in a `file:line` citation; `inputs` has no `netlist`; a file entry has an absolute or
`..` path or a bad sha256; any string holds `/home/`, `/Users/` or an absolute path other than
`/dev/null`. An absolute path is a `/` that starts a string or follows a blank, `=`, `,`, `;`, `:`,
a quote or a bracket and is followed by a path character, so `key=/abs` and `a:/abs` count and
`vpr/src/a.cpp:3`, `a / b` and `https://x` do not. The refusal names the key path and the rule,
never the value.

The writer applies the same rules before it writes (home directory, user name, host name, every real
name of the host map, home path, absolute path). A hit skips that run's record, logs the run id, the
rule and the key path, and the sweep goes on.

## 7. Gates

ruff, `mypy --strict`, unittest (network-free), CI green. A smoke run of one small design with every
placers arm, imported into a fresh store, reported as full against partial per arm with each
non-given parameter and its reason (the lane report).

## 8. Agent defaults

1. The record is per run (one `mimir-run.json` per run directory), not per design.
2. The VPR options come from VPR's own echo; nextpnr settings are enumerated from the source at the
   recorded commit (section 3.3, `scripts/runrecord.py`). A setting with no literal default found is
   `default-unrecorded`.
3. The grid size a nextpnr run was given (`nextpnr.vopt.width`, `height`) is a parameter, so two
   designs of different size have two configurations.
4. Input and artifact hashes stay in the record; the store does not hold them yet.
