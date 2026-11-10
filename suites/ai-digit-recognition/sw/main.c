/* I2 firmware main loop: wait for `start`, read 784 pixels, run the network, publish scores and class.
 * MMIO map: rtl/i2_softcpu/i2_mmio.v. */
#include <stdint.h>
int lenet(const int8_t *img, int8_t *scores);

#define IO ((volatile uint32_t *)0x40000000u)
enum { STAT = 0, PIX = 1 };            /* read word index */
enum { ACK = 0, SC0 = 1, DONE = 4 };   /* write word index */

static int8_t img[784];
static int8_t sc[10];

int main(void) {
    for (;;) {
        while (!(IO[STAT] & 2)) {}
        IO[ACK] = 2;
        for (int i = 0; i < 784; i++) {
            while (!(IO[STAT] & 1)) {}
            img[i] = (int8_t)IO[PIX];
            IO[ACK] = 1;
        }
        int c = lenet(img, sc);
        const uint8_t *b = (const uint8_t *)sc;
        IO[SC0]     = b[0] | (b[1] << 8) | (b[2] << 16) | ((uint32_t)b[3] << 24);
        IO[SC0 + 1] = b[4] | (b[5] << 8) | (b[6] << 16) | ((uint32_t)b[7] << 24);
        IO[SC0 + 2] = b[8] | (b[9] << 8);
        IO[DONE] = (uint32_t)c;
    }
}
