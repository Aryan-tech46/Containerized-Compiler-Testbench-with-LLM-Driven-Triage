// Stress Category: Loop Auto-Vectorizer & Tree-SSA Pass Stress
// Stresses SIMD widening and Induction Variable Optimization (IVOpts)
#include <iostream>
#include <vector>
#include <cmath>

#pragma GCC optimize("O3")

void execute_vector_stress(float* __restrict__ a, float* __restrict__ b, float* __restrict__ out, size_t n) {
    // Multiple induction variables with non-unit strides and pointer aliasing hints
    #pragma GCC ivdep
    for (size_t i = 0; i < n - 3; i += 3) {
        float temp1 = a[i] * b[i + 1] + 1.41421f;
        float temp2 = std::sqrt(std::abs(b[i] * a[i + 2])) + 2.71828f;
        out[i] = (temp1 > temp2) ? temp1 * 0.5f : temp2 * 1.5f;
        out[i + 1] = out[i] + a[i + 2];
    }
}

int main() {
    constexpr size_t N = 1024;
    alignas(64) float arr_a[N];
    alignas(64) float arr_b[N];
    alignas(64) float arr_out[N];

    for (size_t i = 0; i < N; ++i) {
        arr_a[i] = static_cast<float>(i % 17) * 0.1f;
        arr_b[i] = static_cast<float>(i % 23) * 0.2f;
        arr_out[i] = 0.0f;
    }

    execute_vector_stress(arr_a, arr_b, arr_out, N);
    return (arr_out[0] != 0.0f) ? 0 : 1;
}
