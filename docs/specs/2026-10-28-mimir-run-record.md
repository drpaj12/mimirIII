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
| `host` | str | host alias: `host-<n>` or `host-unmapped` (section 5) |
| `kernel` | str | kernel release (no person is identified by it) |
| `started_utc` | str | `YYYY-MM-DDTHH:MM:SSZ` |
| `steps` | list | the tool runs in order (3.1) |
| `time_s`, `peak_rss_mib` | number | the sum of the step times; the largest step RSS |
| `ok` | bool | the last step exited 0 |
| `tools` | object | per tool (3.2) |
| `params` | object | `"step.key"` to `{value, conf, source}` (3.3) |
| `inputs`, `artifacts` | object | role to `{path, sha256}` (3.4) |

### 3.1 `steps`
`{name, argv, exit_code, time_s, peak_rss_mib, locked}`. `argv` is the exact command line of the
tool (without the `flock` and `/usr/bin/time` wrappers); a path is a placeholder: `<run>/x` under the
run directory, `<work>/x`, `<vtr>/x`, a named role such as `<blif>` or `<arch>`, or `<abs>/name` for
any other absolute path. A retried run lists every attempt. `time_s` is the tool's own wall time
(`/usr/bin/time -v`, so a wait for the lock is not counted); `peak_rss_mib` is its maximum resident
set size.

### 3.2 `tools`
Per tool: `commit` (40-hex HEAD of its source tree, or ``), `commit_how`, `clean` (true, false, or
null when there is no tree; tracked files only), `dirty_diff_sha256` (sha256 of `git diff HEAD` when
not clean), `binary_sha256`, `binary_version` (the `--version` text), `version_names_commit` (the
text contains the first 10 characters of `commit`, or, for a script run from its tree, the tree is
clean), and for a tool built from a `git archive` copy `build_copy_differs` (the tracked paths that
differ from HEAD) and `build_copy_is_head` (they are only the paths the build patches).

The commit is a `given` parameter only when `version_names_commit` or `build_copy_is_head` holds;
otherwise it is `unknown`. A dirty tree keeps the commit (the patch is identified by
`dirty_diff_sha256`).

### 3.3 `params`
Every value is a string. `conf` is one of:

- `given`: a source states the value. The source is `command line`, `vpr.out:<line>` (the tool's
  own echo of the effective option, read from the run's log), or a recorded fact. A `given`
  parameter has a non-empty value (write `(empty)` for an empty one).
- `default`: the tool's default, read from the tool source at the recorded commit. The source ends
  in `path:line` or `path:first-last` (for example `vpr/src/base/read_options.cpp:2679-2681`).
- `default-unrecorded`: left to the tool default, but the source is not available.
- `unknown`: no source states it.

The importer counts `unknown` and `default-unrecorded` as non-given: a configuration with one is
`partial`, otherwise `full`.

The keys are `step.key`: `run.seed` (the seed; kept out of the configuration hash, so the seeds of
one setup share a configuration), `run.seed_default`, `tool.<tool>_commit`,
`tool.<tool>_source_clean`, `tool.<tool>_binary_sha256`, `tool.<tool>_dirty_diff_sha256`,
`vpr.<option>` (an option VPR echoed), `vpr.cmd.<flag>` (a flag on the command line),
`nextpnr.cmd.<flag>`, `nextpnr.vopt.<key>`, `nextpnr.<setting>` (a default). A runner may add keys;
the importer takes the part before the first `.` as the step.

VPR echoes its effective options (netlist, analytical placer, router and analysis groups; the
placer group when the annealer runs); an option that VPR neither echoes nor receives on the command
line is not in the record. The echo is a statement of the run itself, so it is `given`.

### 3.4 `inputs`, `artifacts`
`{path, sha256}`: `path` is relative (a placeholder prefix is allowed, never a leading `/` and
never `..`), `sha256` is 64 hex. The role `netlist` is required in `inputs`: its sha256 is the
run's input identity. The role `arch` becomes the parameter `arch.arch_file_sha256`.

## 4. Import (`mimir import-runrecords <db> <dir>`)

Every `mimir-run.json` under `<dir>` is read and checked (section 6). A record that fails is
refused and listed with every reason; the others are imported and the exit code is 1 when any was
refused. For each valid record:

- `flow_config`: name `<source>/<arm>`, text = the step command lines joined by newlines with the
  value after `--seed` replaced by `<seed>`, `text_kind` = `recorded-normalised`, origin
  `mimir-run.json record_version 1`; its parameters are the record's, with the conf as recorded.
  The configuration hash is `Spec.config_hash` (seed excluded).
- `flow_param`: one row per record parameter, plus `arch.arch_file_sha256`.
- `run`: key `(source, design, arch, seed, arm)`, `tool_commit` = the VPR commit when VPR ran
  (otherwise the first tool's), `input_sha256` = the netlist sha256, `command_line`, `time_s`,
  `peak_rss_mib` and `host` from the record, `tool_commits` = `tool=commit[-dirty]` pairs.

Existing reconstructed runs are never changed: the records have their own `source`. Importing the
same records again changes nothing.

## 5. Host alias

`$MIMIR_HOST_MAP` names a TOML file of `"real name" = "host-<n>"` lines (flat or in a `[hosts]`
table); the file is local and never committed. The writer looks the real name up (case
insensitive); an unknown name gets the next `host-<n>` and the line is appended; without a map the
alias is `host-unmapped`. The real name is never written to a record.

## 6. Validation (what the importer refuses)

A record is refused when: `record_version` is not 1 or a required key is missing or has the wrong
type; `kind` is unknown; `family` is not a schema family; `host` is not `host-<n>` or
`host-unmapped`; `steps` is empty or a step lacks a field; a tool commit is not `` or 40-hex or a
`binary_sha256` is not `` or 64-hex; a parameter lacks `value`, `conf` or `source`, has an unknown
`conf`, has an empty `source`, is `given` with an empty value, or is `default` with a source that
does not end in a `file:line` citation; `inputs` has no `netlist`; a file entry has an absolute or
`..` path or a bad sha256; any string holds `/home/`, `/Users/` or an absolute path other than
`/dev/null`.

## 7. Gates

ruff, `mypy --strict`, unittest (network-free), CI green. A smoke run of one small design with every
placers arm, imported into a fresh store, reported as full against partial per arm with each
non-given parameter and its reason (the lane report).

## 8. Agent defaults

1. The record is per run (one `mimir-run.json` per run directory), not per design.
2. The VPR options come from VPR's own echo; nextpnr defaults come from a table of the settings the
   chosen placer reads (`scripts/runrecord.py`), each verified by finding its source line in the
   tool tree at run time. A setting whose line is not found is `default-unrecorded`.
3. The grid size a nextpnr run was given (`nextpnr.vopt.width`, `height`) is a parameter, so two
   designs of different size have two configurations.
4. Input and artifact hashes stay in the record; the store does not hold them yet.
