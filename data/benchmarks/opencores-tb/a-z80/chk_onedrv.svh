// Included inside tb_cmp when CHK_ONEDRV is defined (modified DUT only; uses hierarchical references).
// Check: in every connected component of the internal data-bus graph (segments joined by enabled switch paths),
// at most one driver enable is active. Segments: S0=db0 S1=db1 S2=db2 T0/T1=register bus lo/hi A0/A1=address-side lo/hi.
// Also: no switch path is enabled in both directions, and the five ALU internal bus sources are mutually exclusive.
integer od_samples = 0, od_viol = 0, od_pair = 0, od_alu = 0, od_floating = 0, od_maxsrc = 0, od_i, od_k;
reg [6:0] src_cnt_dummy;
integer cnt [0:6];
integer comp [0:6];
reg [5:0] edge_on;
task automatic od_check;
  integer s0, s1, s2, t0, t1, a0, a1, changed, n;
  reg e01, e12, e1t0, e2t1, et0a0, et1a1;
  begin
    s0 = (dw.u.ctl_bus_db_oe ? 1 : 0) + ((dw.u.ctl_bus_ff_oe | dw.u.ctl_bus_zero_oe) ? 1 : 0);
    s1 = ((dw.u.ctl_66_oe | dw.u.ctl_daa_oe) ? 1 : 0) + (dw.u.ctl_flags_oe ? 1 : 0);
    s2 = dw.u.alu_.alu_oe ? 1 : 0;
    t0 = dw.u.reg_file_.b2v_latch_af2_lo.oe + dw.u.reg_file_.b2v_latch_af_lo.oe + dw.u.reg_file_.b2v_latch_bc2_lo.oe + dw.u.reg_file_.b2v_latch_bc_lo.oe
       + dw.u.reg_file_.b2v_latch_de2_lo.oe + dw.u.reg_file_.b2v_latch_de_lo.oe + dw.u.reg_file_.b2v_latch_hl2_lo.oe + dw.u.reg_file_.b2v_latch_hl_lo.oe
       + dw.u.reg_file_.b2v_latch_ix_lo.oe + dw.u.reg_file_.b2v_latch_iy_lo.oe + dw.u.reg_file_.b2v_latch_sp_lo.oe + dw.u.reg_file_.b2v_latch_wz_lo.oe;
    t1 = dw.u.reg_file_.b2v_latch_af2_hi.oe + dw.u.reg_file_.b2v_latch_af_hi.oe + dw.u.reg_file_.b2v_latch_bc2_hi.oe + dw.u.reg_file_.b2v_latch_bc_hi.oe
       + dw.u.reg_file_.b2v_latch_de2_hi.oe + dw.u.reg_file_.b2v_latch_de_hi.oe + dw.u.reg_file_.b2v_latch_hl2_hi.oe + dw.u.reg_file_.b2v_latch_hl_hi.oe
       + dw.u.reg_file_.b2v_latch_ix_hi.oe + dw.u.reg_file_.b2v_latch_iy_hi.oe + dw.u.reg_file_.b2v_latch_sp_hi.oe + dw.u.reg_file_.b2v_latch_wz_hi.oe;
    a0 = dw.u.reg_file_.b2v_latch_ir_lo.oe + dw.u.reg_file_.b2v_latch_pc_lo.oe + (dw.u.ctl_bus_inc_oe ? 1 : 0);
    a1 = dw.u.reg_file_.b2v_latch_ir_hi.oe + dw.u.reg_file_.b2v_latch_pc_hi.oe + (dw.u.ctl_bus_inc_oe ? 1 : 0);
    e01 = dw.u.bus_sw_1u | dw.u.bus_sw_1d;  e12 = dw.u.bus_sw_2u | dw.u.bus_sw_2d;
    e1t0 = dw.u.ctl_reg_in_lo | dw.u.ctl_reg_out_lo;  e2t1 = dw.u.ctl_reg_in_hi | dw.u.ctl_reg_out_hi;
    et0a0 = dw.u.ctl_sw_4u | dw.u.reg_sw_4d_lo;  et1a1 = dw.u.ctl_sw_4u | dw.u.reg_sw_4d_hi;
    // pairs enabled in both directions
    if ((dw.u.bus_sw_1u & dw.u.bus_sw_1d) | (dw.u.bus_sw_2u & dw.u.bus_sw_2d) | (dw.u.ctl_reg_in_lo & dw.u.ctl_reg_out_lo)
      | (dw.u.ctl_reg_in_hi & dw.u.ctl_reg_out_hi) | (dw.u.ctl_sw_4u & dw.u.reg_sw_4d_lo) | (dw.u.ctl_sw_4u & dw.u.reg_sw_4d_hi)) od_pair = od_pair + 1;
    // ALU internal bus
    if ((dw.u.alu_.alu_bs_oe + dw.u.alu_.alu_op2_oe + dw.u.alu_.alu_res_oe + dw.u.alu_.alu_op1_oe + dw.u.alu_.alu_shift_oe) > 1) od_alu = od_alu + 1;
    // components of the tree S0-S1-S2, S1-T0-A0, S2-T1-A1 (labels = lowest node index reachable)
    for (od_i = 0; od_i < 7; od_i = od_i + 1) comp[od_i] = od_i;
    changed = 1;
    while (changed) begin
      changed = 0;
      if (e01  && comp[0] != comp[1]) begin n = (comp[0] < comp[1]) ? comp[0] : comp[1]; comp[0] = n; comp[1] = n; changed = 1; end
      if (e12  && comp[1] != comp[2]) begin n = (comp[1] < comp[2]) ? comp[1] : comp[2]; comp[1] = n; comp[2] = n; changed = 1; end
      if (e1t0 && comp[1] != comp[3]) begin n = (comp[1] < comp[3]) ? comp[1] : comp[3]; comp[1] = n; comp[3] = n; changed = 1; end
      if (e2t1 && comp[2] != comp[4]) begin n = (comp[2] < comp[4]) ? comp[2] : comp[4]; comp[2] = n; comp[4] = n; changed = 1; end
      if (et0a0 && comp[3] != comp[5]) begin n = (comp[3] < comp[5]) ? comp[3] : comp[5]; comp[3] = n; comp[5] = n; changed = 1; end
      if (et1a1 && comp[4] != comp[6]) begin n = (comp[4] < comp[6]) ? comp[4] : comp[6]; comp[4] = n; comp[6] = n; changed = 1; end
      // propagate labels through already-joined nodes (second pass handles chains)
      for (od_i = 0; od_i < 7; od_i = od_i + 1) cnt[od_i] = 0;
    end
    for (od_i = 0; od_i < 7; od_i = od_i + 1) cnt[od_i] = 0;
    cnt[comp[0]] = cnt[comp[0]] + s0; cnt[comp[1]] = cnt[comp[1]] + s1; cnt[comp[2]] = cnt[comp[2]] + s2;
    cnt[comp[3]] = cnt[comp[3]] + t0; cnt[comp[4]] = cnt[comp[4]] + t1; cnt[comp[5]] = cnt[comp[5]] + a0; cnt[comp[6]] = cnt[comp[6]] + a1;
    for (od_i = 0; od_i < 7; od_i = od_i + 1) begin
      if (cnt[od_i] > 1) od_viol = od_viol + 1;
      if (cnt[od_i] > od_maxsrc) od_maxsrc = cnt[od_i];
    end
    od_samples = od_samples + 1;
  end
endtask
always @(posedge CLK or negedge CLK) begin #0.3; od_check; end
final $display("ONEDRV samples=%0d component_violations=%0d both_directions=%0d alu_bus_multi=%0d max_sources_in_a_component=%0d", od_samples, od_viol, od_pair, od_alu, od_maxsrc);
