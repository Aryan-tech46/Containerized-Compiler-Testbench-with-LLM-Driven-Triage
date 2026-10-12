// Deliberate SFINAE / concept recursion limit violation
#include <type_traits>
template <typename T> struct InfiniteRec : InfiniteRec<T*> {};
int main() { InfiniteRec<int> x; return 0; }
