# Golden provenance

- Network and program: `Benchmarks/LeNet_5_TRANSMISSION.bin` of external/USS_Tensor_Processing_Unit (Gabe Litteken, MIT),
  read by path, never copied. Message Protocol v0.3: `U`, `M` block (address 2, 60,074 bytes: weights and biases
  contiguous in order conv1.w, conv1.b, conv2.w, ...), 1,350 `P` instructions, `S`.
- Layout facts found from the program (not from his npz): conv weights are `[out, in*kh*kw]` row-major (left
  operand); fc weights are stored `[in, out]` (right operand of a row-vector matmul). (M0, n) per layer from the MUL
  instructions: conv1 (181,16), conv2 (183,17), fc1 (143,16), fc2 (206,16), fc3 (174,16).
- The bin's weights differ from `System/Neural_Networks/LeNet_5/LeNet_5_Recent.weights.npz` (the npz that his
  `Emulator.py` loads): different quantised values and (M0, n). Both are checked in `tools/check_golden.py`.
- `S_in` is not in the bin. 0.02268019 (the npz conv1 input scale) gives 98.74 % top-1, consistent with a
  retrained network; the real value used when the bin was made is unconfirmed (open item).
