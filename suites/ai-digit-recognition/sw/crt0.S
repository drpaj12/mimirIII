/* I2 start-up: stack pointer, call main, park. No .data/.bss initialisation is needed (no
 * initialised writable data; the static buffers are written before they are read). */
    .section .text.start
    .globl _start
_start:
    la sp, _stack_top
    call main
1:  j 1b
