"""timing_rerun: architecture lookup, stored VPR options, argument building (no VPR run)."""

from __future__ import annotations

import unittest

from mimir import timingrerun as tr

LOG = ("=== vpr/vpr.log\nVPR was run with the following command-line:\n"
       "$VTR_ROOT/vpr/vpr k6.xml top --circuit_file top.pre-vpr.blif --max_router_iterations 100 "
       "--route --analysis --route_chan_width 60 --clock_modeling ideal\n\nUsing up to 1\n")


class Rerun(unittest.TestCase):
    def test_arch_known_and_unknown(self) -> None:
        self.assertTrue(tr.arch_path("k6_frac_N10_frac_chain_mem32K_40nm.xml").endswith(".xml"))
        with self.assertRaises(ValueError):
            tr.arch_path("other.xml")

    def test_options_carried_and_left_out(self) -> None:
        carry, left = tr.carried_options(tr.stored_vpr_argv(LOG))
        self.assertEqual(carry, ["--route_chan_width", "60", "--clock_modeling", "ideal"])
        self.assertEqual(left, ["--max_router_iterations"])

    def test_missing_chan_width_aborts(self) -> None:
        with self.assertRaises(ValueError):
            tr.carried_options(["--circuit_file", "x.blif"])

    def test_no_command_in_log(self) -> None:
        with self.assertRaises(ValueError):
            tr.stored_vpr_argv("nothing here")

    def test_argv(self) -> None:
        argv = tr.vpr_argv("vpr", "a.xml", "top", ["--route_chan_width", "60"], 5000)
        self.assertEqual(argv[:3], ["vpr", "a.xml", "top"])
        self.assertIn("--analysis", argv)
        self.assertEqual(argv[argv.index("--timing_report_npaths") + 1], "5000")
        for flag in ("--route", "--pack", "--place"):
            self.assertNotIn(flag, argv)  # nothing is re-placed or re-routed
        self.assertEqual(argv[argv.index("--route_file") + 1], "top.route")


if __name__ == "__main__":
    unittest.main()
