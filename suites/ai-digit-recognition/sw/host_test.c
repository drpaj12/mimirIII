/* Host check of sw/lenet.c against the golden vectors: host_test <vec_dir> <n> ; prints mismatches. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
int lenet(const int8_t *img, int8_t *scores);

static uint8_t *readhex(const char *dir, const char *name, long n) {
    char p[512];
    snprintf(p, sizeof p, "%s/%s", dir, name);
    FILE *f = fopen(p, "r");
    if (!f) { perror(p); exit(2); }
    uint8_t *b = malloc(n);
    for (long i = 0; i < n; i++) { unsigned v; if (fscanf(f, "%x", &v) != 1) exit(3); b[i] = v; }
    fclose(f);
    return b;
}

int main(int argc, char **argv) {
    long n = atol(argv[2]);
    uint8_t *img = readhex(argv[1], "vec_images.hex", n * 784);
    uint8_t *gs = readhex(argv[1], "vec_gscores.hex", n * 10);
    uint8_t *gc = readhex(argv[1], "vec_gclass.hex", n);
    uint8_t *lab = readhex(argv[1], "vec_labels.hex", n);
    long cm = 0, sm = 0, lc = 0;
    for (long i = 0; i < n; i++) {
        int8_t s[10];
        int c = lenet((int8_t *)(img + i * 784), s);
        int ok = 1;
        for (int k = 0; k < 10; k++) ok &= (uint8_t)s[k] == gs[i * 10 + k];
        cm += c == gc[i]; sm += ok; lc += c == lab[i];
    }
    printf("host n=%ld class_match=%ld score_match=%ld label_correct=%ld\n", n, cm, sm, lc);
    return !(cm == n && sm == n);
}
