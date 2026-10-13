// Stress Category: C++20 Concepts & Nested Requires Constraints
// Stresses frontend AST constraint satisfaction and fold expression deduction
#include <iostream>
#include <concepts>
#include <type_traits>

template <typename T>
concept ArithmeticScalar = std::is_arithmetic_v<T>;

template <typename T>
concept NestedTransformable = requires(T a) {
    { a * 2 } -> std::same_as<T>;
    { a + 1 } -> std::convertible_to<int>;
};

template <typename T>
concept DeeplyConstrained = ArithmeticScalar<T> && NestedTransformable<T> && requires(T val) {
    requires sizeof(T) <= 8;
    requires (sizeof(val) > 0);
};

// Recursive constraint evaluation across type packs
template <typename Head, typename... Tail>
requires DeeplyConstrained<Head> && (DeeplyConstrained<Tail> && ...)
constexpr auto evaluate_pack(Head h, Tail... tail) {
    if constexpr (sizeof...(tail) == 0) {
        return h;
    } else {
        return h + evaluate_pack(tail...);
    }
}

int main() {
    auto res = evaluate_pack(10, 20L, 30.5f);
    (void)res;
    return 0;
}
