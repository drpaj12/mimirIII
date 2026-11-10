/* ROM (code + weights) at 0, RAM at 0x10000000; sizes from the build (ROM_BYTES, RAM_BYTES). */
ENTRY(_start)
MEMORY {
  ROM (rx)  : ORIGIN = 0x00000000, LENGTH = ROM_BYTES
  RAM (rwx) : ORIGIN = 0x10000000, LENGTH = RAM_BYTES
}
SECTIONS {
  .text : { *(.text.start) *(.text*) } > ROM
  .rodata : { *(.rodata*) *(.srodata*) } > ROM
  .bss (NOLOAD) : { *(.sbss*) *(.bss*) *(COMMON) } > RAM
  _stack_top = ORIGIN(RAM) + LENGTH(RAM);
}
