// Stress Category: Recursive Concept Dependency Cycle
// Provokes circular concept constraint satisfaction failure
#include <concepts>

template <typename T>
concept ConceptA = requires(T a) {
    { a.process() };
};

template <typename T>
concept ConceptB = ConceptA<T> && requires(T b) {
    { b.validate() };
};

// Deliberately violates concept contract on non-conforming struct
struct NonConforming {
    void process() {}
};

template <ConceptB T>
void execute_safe(T obj) {
    obj.validate();
}

int main() {
    NonConforming item;
    execute_safe(item); // Constraint failure: item does not satisfy ConceptB
    return 0;
}
