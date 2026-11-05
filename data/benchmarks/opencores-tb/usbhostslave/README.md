# usbhostslave testbench

tb_origin: `upstream-fixed`. The project's own bench (`bench/sepHostSlaveTestHarness.v`, `bench/testCase0.v`,
`model/wb_master_model.v`) is used unchanged. Only fix: `filelistSepHostSlave.icarus.patch` corrects the
letter case of file names in `sim/filelistSepHostSlave.icarus` (written on Windows, e.g. `directControl.v`
vs `directcontrol.v`); RTL and bench untouched. Upstream licence applies (LGPL 2.1 or later).
Found by the OpenCores candidates survey (controller note 2026-11-04) and reproduced here.

Checks (the bench's own): 12 test steps, each prints `--- PASSED`; then `Finished all tests`
(`testCase0.v:247: $stop`, 166521000 ticks). Run result: 12 PASSED, no error or fail line.
The combo harness (`comboHostSlaveTestHarness.v`) does not compile (`EP3_FIFO_ADDR_WIDTH` declared twice):
not used.

Run (iverilog 2005 mode), in a copy of the project with the patched file list, from `sim/`
(the bench dumps `wave.vcd`, 371 MB, delete or redirect it):

    iverilog -g2005 -o testHarness -cfilelistSepHostSlave.icarus && vvp testHarness

Odin III: not run to the end. Reading the RTL list without include directories stops at
`include_not_found: 'timescale.v'`; the bench uses includes, tasks and hierarchical references, outside
the sim_tb subset (not tried further).
