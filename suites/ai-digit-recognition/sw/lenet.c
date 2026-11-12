/* int8 LeNet-5, C port of golden/lenet_int8.py (docs/GOLDEN.md). Shared by the host check and the
 * soft-CPU firmware. Weights come from the generated weights.c.
 *
 * Exactness: y = clip((M0*acc + (1<<(n-1))) >> n, -128, 127), arithmetic shift. Values fit int32
 * (|acc| < 2^20, M0 < 256 for conv; fc1 acc < 2^23, M0 143). max-pool and ReLU commute with the
 * monotone requant, so the max is taken on the accumulators and requantised once; this equals the
 * golden (requant, relu, pool) and skips three of four requants. The 11th conv2 row/column is
 * dropped by the 2x2 floor pool in the golden, so it is not computed.
 * MUL8(a,b): hardware `*` by default; -DSOFTMUL=1 uses the quarter-square table
 * ab = q(|a+b|) - q(|a-b|), q(x) = floor(x*x/4) (exact: a+b and a-b have the same parity).
 */
#include <stdint.h>
#include "weights.h"

#if defined(SOFTMUL) && SOFTMUL
static inline int mul8(int a, int b) {
    int s = a + b, d = a - b;
    return (int)QSQ[s < 0 ? -s : s] - (int)QSQ[d < 0 ? -d : d];
}
#else
static inline int mul8(int a, int b) { return a * b; }
#endif

static inline int rq(int acc, int m0, int n) {
    int v = (m0 * acc + (1 << (n - 1))) >> n;
    return v < -128 ? -128 : (v > 127 ? 127 : v);
}

static int8_t p1[6 * 13 * 13];
static int8_t p2[400];
static int8_t f1[120];
static int8_t f2[84];

static void conv1_pool(const int8_t *img) {
    for (int oc = 0; oc < 6; oc++) {
        const int8_t *w = W_CONV1 + oc * 9;
        for (int py = 0; py < 13; py++)
            for (int px = 0; px < 13; px++) {
                int best = -0x7fffffff;
                for (int dy = 0; dy < 2; dy++)
                    for (int dx = 0; dx < 2; dx++) {
                        const int8_t *x = img + (2 * py + dy) * 28 + 2 * px + dx;
                        int acc = mul8(w[0], x[0]) + mul8(w[1], x[1]) + mul8(w[2], x[2])
                                + mul8(w[3], x[28]) + mul8(w[4], x[29]) + mul8(w[5], x[30])
                                + mul8(w[6], x[56]) + mul8(w[7], x[57]) + mul8(w[8], x[58]);
                        if (acc > best) best = acc;
                    }
                int v = rq(best, M0_CONV1, N_CONV1);
                p1[oc * 169 + py * 13 + px] = (int8_t)(v < 0 ? 0 : v);
            }
    }
}

static void conv2_pool(void) {
    for (int oc = 0; oc < 16; oc++)
        for (int py = 0; py < 5; py++)
            for (int px = 0; px < 5; px++) {
                int best = -0x7fffffff;
                for (int dy = 0; dy < 2; dy++)
                    for (int dx = 0; dx < 2; dx++) {
                        const int8_t *w = W_CONV2 + oc * 54;
                        const int8_t *x = p1 + (2 * py + dy) * 13 + 2 * px + dx;
                        int acc = 0;
                        for (int c = 0; c < 6; c++, w += 9, x += 169)
                            acc += mul8(w[0], x[0]) + mul8(w[1], x[1]) + mul8(w[2], x[2])
                                 + mul8(w[3], x[13]) + mul8(w[4], x[14]) + mul8(w[5], x[15])
                                 + mul8(w[6], x[26]) + mul8(w[7], x[27]) + mul8(w[8], x[28]);
                        if (acc > best) best = acc;
                    }
                int v = rq(best, M0_CONV2, N_CONV2);
                p2[oc * 25 + py * 5 + px] = (int8_t)(v < 0 ? 0 : v);
            }
}

static void fc(const int8_t *w, const int8_t *in, int nin, int nout, int8_t *out, int m0, int n,
               int relu) {
    for (int o = 0; o < nout; o++, w += nin) {
        int acc = 0;
        for (int i = 0; i < nin; i += 4)
            acc += mul8(w[i], in[i]) + mul8(w[i + 1], in[i + 1]) + mul8(w[i + 2], in[i + 2])
                 + mul8(w[i + 3], in[i + 3]);
        int v = rq(acc, m0, n);
        out[o] = (int8_t)(relu && v < 0 ? 0 : v);
    }
}

/* img: 784 int8 (already quantised); scores: 10 int8; returns the class (first max wins) */
int lenet(const int8_t *img, int8_t *scores) {
    conv1_pool(img);
    conv2_pool();
    fc(W_FC1, p2, 400, 120, f1, M0_FC1, N_FC1, 1);
    fc(W_FC2, f1, 120, 84, f2, M0_FC2, N_FC2, 1);
    fc(W_FC3, f2, 84, 10, scores, M0_FC3, N_FC3, 0);
    int best = 0;
    for (int k = 1; k < 10; k++)
        if (scores[k] > scores[best]) best = k;
    return best;
}
