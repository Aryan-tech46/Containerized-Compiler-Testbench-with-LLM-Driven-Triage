// Stress Category: Deep Inliner Call Chains & Generic Lambdas
// Stresses GIMPLE inliner pass and devirtualization tree depth
#include <iostream>

#define ALWAYS_INLINE inline __attribute__((always_inline))

ALWAYS_INLINE int stage_10(int x) { return x ^ 0xA5; }
ALWAYS_INLINE int stage_9(int x)  { return stage_10(x + 1) * 2; }
ALWAYS_INLINE int stage_8(int x)  { return stage_9(x - 3) ^ 0x55; }
ALWAYS_INLINE int stage_7(int x)  { return stage_8(x * 3) + 7; }
ALWAYS_INLINE int stage_6(int x)  { return stage_7(x + 2) ^ 0x33; }
ALWAYS_INLINE int stage_5(int x)  { return stage_6(x * 2) - 5; }
ALWAYS_INLINE int stage_4(int x)  { return stage_5(x + 4) ^ 0x0F; }
ALWAYS_INLINE int stage_3(int x)  { return stage_4(x - 1) + 9; }
ALWAYS_INLINE int stage_2(int x)  { return stage_3(x * 4) ^ 0xFF; }
ALWAYS_INLINE int stage_1(int x)  { return stage_2(x + 5) - 3; }

int main() {
    // Nested generic lambda invocation passing through always_inline chain
    auto dispatcher = [](auto val, auto next_fn) {
        return next_fn(val) + 1;
    };

    int result = dispatcher(42, [](int v) {
        return stage_1(v);
    });

    return (result != 0) ? 0 : 1;
}
