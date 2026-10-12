// Stress Category: Deep Template Metaprogramming Recursion
// Target Depth: 300
#include <iostream>
#include <type_traits>

template <int N>
struct RecursiveFactorial {
    static constexpr unsigned long long value = N * RecursiveFactorial<N - 1>::value;
};

template <>
struct RecursiveFactorial<0> {
    static constexpr unsigned long long value = 1;
};

// Recursive type-list unwrapping
template <typename... Ts>
struct TypeList {};

template <typename Head, typename... Tail>
struct TypeListLength {
    static constexpr size_t value = 1 + TypeListLength<Tail...>::value;
};

template <typename Head>
struct TypeListLength<Head> {
    static constexpr size_t value = 1;
};

template <int N>
struct PeanoNat {
    using Prev = PeanoNat<N - 1>;
    static constexpr int val = N;
};

template <>
struct PeanoNat<0> {
    static constexpr int val = 0;
};

// Deep nested inheritance recursion
template <int Depth>
struct DeepTemplateChain : DeepTemplateChain<Depth - 1> {
    using Sub = DeepTemplateChain<Depth - 1>;
    constexpr int compute() const {
        return Depth + Sub::compute();
    }
};

template <>
struct DeepTemplateChain<0> {
    constexpr int compute() const {
        return 0;
    }
};

// SFINAE stress with expression substitution
template <typename T, typename = std::enable_if_t<(sizeof(T) > 0)>>
constexpr auto sfinae_check(T val) -> decltype(val + 1) {
    return val + 1;
}

int main() {
    constexpr auto fact_val = RecursiveFactorial<20>::value;
    DeepTemplateChain<300> chain;
    volatile int res = chain.compute();
    volatile auto sfinae_res = sfinae_check(res);
    (void)fact_val;
    (void)sfinae_res;
    return 0;
}
