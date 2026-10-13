// Stress Category: Exceeded Template Recursion Depth Limit
// Provokes compiler frontend depth cutoff (default max 900)
#include <iostream>

template <int N>
struct RecursiveLimitStress {
    static constexpr int val = 1 + RecursiveLimitStress<N - 1>::val;
};

template <>
struct RecursiveLimitStress<0> {
    static constexpr int val = 0;
};

int main() {
    // Depth 1500 intentionally exceeds GCC default depth limit of 900
    constexpr int result = RecursiveLimitStress<1500>::val;
    return result;
}
