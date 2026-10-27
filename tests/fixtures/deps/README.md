# Vendored test copies of the two libraries lane 3 imports

`mimir.structmap.load_deps` imports Odin III's `name_map_v2` and Loki's `loki.audit.units` and
`loki.audit.loss` as libraries. The production code never uses these copies. They exist only so the
unit tests run in CI, where neither checkout is present. The tests use them when
`MIMIR_ODIN3_TREE` and `MIMIR_LOKI_SRC` are not set (`tests/depsfix.py`), and the real checkouts
when they are.

| File | Origin | Last commit touching it | sha256 |
|---|---|---|---|
| `tools/flow/name_map_v2.py` | odin3 `tools/flow/name_map_v2.py` | 513414fe7f62b83660542c01faff5bc2b4819511 | 9b743d51dcf97a77361c65e7cfa4b98005d3558b21ca4f44dffaae85f5d11e97 |
| `loki/audit/__init__.py` | loki `loki/audit/__init__.py` | 53a7d9bf451605f0aa1b1cd57db49f64d25d4c1b | cf9838bad9fece10e7fdffab49321f25b80fc742ccaf5a25c9ae66d36597a3e6 |
| `loki/audit/units.py` | loki `loki/audit/units.py` | 53a7d9bf451605f0aa1b1cd57db49f64d25d4c1b | 8a833d1d449fd64462f90a784c79c790fada5f5f54a13118313da78056ca7638 |
| `loki/audit/loss.py` | loki `loki/audit/loss.py` | 53a7d9bf451605f0aa1b1cd57db49f64d25d4c1b | bd3ead1b9c4c1c56891d5fe56a631bd07c0cbf2215290c1c67ef1536c36dfab9 |
| `loki/__init__.py` | empty stub (the real one only holds `__version__`) | | |

Both files are standard library only. Do not edit them; copy them again from the sources.
