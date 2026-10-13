// Stress Category: Ambiguous SFINAE Overload Conflict
// Provokes frontend overload resolution ambiguity
#include <type_traits>

template <typename T, typename = std::enable_if_t<sizeof(T) >= 1>>
int evaluate_candidate(T val) {
    return static_cast<int>(val) * 2;
}

template <typename T, typename = std::enable_if_t<std::is_integral<T>::value>>
int evaluate_candidate(T val) {
    return static_cast<int>(val) * 3;
}

int main() {
    // Both template overloads have equal substitution specificity for int
    int result = evaluate_candidate(42);
    return result;
}
