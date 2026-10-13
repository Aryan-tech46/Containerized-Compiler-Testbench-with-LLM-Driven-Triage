// Stress Category: Constexpr Step Limit Exhaustion
// Provokes compile-time interpreter cutoff
constexpr long long calculate_excessive_steps(long long count) {
    long long acc = 0;
    for (long long i = 0; i < count; ++i) {
        acc += (i & 1) ? 1 : -1;
    }
    return acc;
}

int main() {
    // Step count 200,000,000 exceeds constexpr iteration limit (262,144)
    constexpr long long val = calculate_excessive_steps(200000000LL);
    return static_cast<int>(val);
}
