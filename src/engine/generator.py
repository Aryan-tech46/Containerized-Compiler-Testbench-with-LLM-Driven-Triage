"""Compiler Test Generator module.

Generates syntactically valid yet highly complex C++ source files targeting
known compiler stress areas:
1. Deep template metaprogramming recursion (SFINAE & C++20 concepts)
2. Complex pointer arithmetic and aliasing
3. Heavy inline assembly and volatile memory manipulation
4. Concurrency edge cases with uninitialized memory
5. Tree-SSA auto-vectorizer and loop transformation stress
6. Deep inliner call chains and generic lambda closures
"""

import json
import os
import random
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple


@dataclass
class TestMetadata:
    """Rich metadata describing a generated synthetic test case."""
    filepath: str
    category: str
    target_pass: str
    expected_outcome: str  # "PASS" | "COMPILE_ERROR" | "STRESS"
    compiler_flags: str
    description: str


class CompilerTestGenerator:
    """Generates synthetic C++ edge-case source files designed to stress compilers."""

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)

    def generate_template_recursion(self, depth: int = 450) -> str:
        """Emits C++ source code with deep template recursion and SFINAE type lists."""
        types = ["int", "long", "short", "unsigned int", "char"]
        chosen_type = self.rng.choice(types)

        return f"""// Stress Category: Deep Template Metaprogramming Recursion
// Target Depth: {depth} | Base Type: {chosen_type}
#include <iostream>
#include <type_traits>

template <int N>
struct RecursiveFactorial {{
    static constexpr unsigned long long value = N * RecursiveFactorial<N - 1>::value;
}};

template <>
struct RecursiveFactorial<0> {{
    static constexpr unsigned long long value = 1;
}};

// Recursive type-list unwrapping
template <typename... Ts>
struct TypeList {{}};

template <typename Head, typename... Tail>
struct TypeListLength {{
    static constexpr size_t value = 1 + TypeListLength<Tail...>::value;
}};

template <typename Head>
struct TypeListLength<Head> {{
    static constexpr size_t value = 1;
}};

template <int N>
struct PeanoNat {{
    using Prev = PeanoNat<N - 1>;
    static constexpr int val = N;
}};

template <>
struct PeanoNat<0> {{
    static constexpr int val = 0;
}};

// Deep nested inheritance recursion
template <int Depth>
struct DeepTemplateChain : DeepTemplateChain<Depth - 1> {{
    using Sub = DeepTemplateChain<Depth - 1>;
    constexpr {chosen_type} compute() const {{
        return static_cast<{chosen_type}>(Depth) + Sub::compute();
    }}
}};

template <>
struct DeepTemplateChain<0> {{
    constexpr {chosen_type} compute() const {{
        return 0;
    }}
}};

// SFINAE stress with expression substitution
template <typename T, typename = std::enable_if_t<(sizeof(T) > 0)>>
constexpr auto sfinae_check(T val) -> decltype(val + 1) {{
    return val + 1;
}}

int main() {{
    constexpr auto fact_val = RecursiveFactorial<{min(depth, 20)}>::value;
    DeepTemplateChain<{min(depth, 500)}> chain;
    volatile {chosen_type} res = chain.compute();
    volatile auto sfinae_res = sfinae_check(res);
    (void)fact_val;
    (void)sfinae_res;
    return 0;
}}
"""

    def generate_pointer_aliasing(self, dimensions: int = 16) -> str:
        """Emits C++ source code with complex multidimensional pointer arithmetic,

        reinterpret_cast stress, and strict aliasing barriers.
        """
        xor_mask = self.rng.choice([0xDEADBEEFCAFEBABE, 0x123456789ABCDEF0, 0xA5A5A5A55A5A5A5A])

        return f"""// Stress Category: Complex Pointer Arithmetic and Aliasing
#include <iostream>
#include <cstdint>
#include <cstring>
#include <vector>

union AliasingUnion {{
    uint64_t u64[4];
    uint32_t u32[8];
    uint8_t  u8[32];
    double   d64[4];
}};

// Complex pointer stepping through multidimensional array decay
void stress_aliasing(volatile char* buffer, size_t len) {{
    uintptr_t raw_addr = reinterpret_cast<uintptr_t>(buffer);
    uintptr_t aligned_addr = (raw_addr + 31) & ~static_cast<uintptr_t>(31);
    
    AliasingUnion* u_ptr = reinterpret_cast<AliasingUnion*>(aligned_addr);
    
    for (size_t i = 0; i < 4; ++i) {{
        u_ptr->u64[i] = 0x{xor_mask:X}ULL ^ (i * 0x101010101010101ULL);
    }}
    
    // Strict aliasing stress: pointer reinterpretation across types
    uint32_t* p32 = reinterpret_cast<uint32_t*>(u_ptr->u8 + 7);
    volatile uint32_t read_val = *p32;
    *p32 = read_val ^ 0xAAAA5555;
    
    // Multidimensional offset folding
    int32_t matrix[{dimensions}][{dimensions}];
    int32_t* base = &matrix[0][0];
    for (int r = 0; r < {dimensions}; ++r) {{
        for (int c = 0; c < {dimensions}; ++c) {{
            ptrdiff_t offset = (r * {dimensions}) + c;
            *(base + offset) = (r ^ c) + static_cast<int32_t>(read_val);
        }}
    }}
}}

int main() {{
    alignas(64) char raw_buffer[512];
    std::memset(raw_buffer, 0x5A, sizeof(raw_buffer));
    stress_aliasing(raw_buffer, sizeof(raw_buffer));
    return 0;
}}
"""

    def generate_inline_asm_volatile(self) -> str:
        """Emits C++ code stressing inline assembly constraints, clobbers, and volatile memory."""
        xor_key = self.rng.choice([0x55AA55AA, 0x0F0F0F0F, 0xDEADBEEF])

        return f"""// Stress Category: Heavy Inline Assembly and Volatile Memory Manipulation
#include <iostream>
#include <cstdint>

// Volatile hardware register emulation
struct HardwareRegisterBlock {{
    volatile uint32_t CONTROL;
    volatile uint32_t STATUS;
    volatile uint32_t DATA_IN;
    volatile uint32_t DATA_OUT;
}};

void execute_asm_pipeline(uint32_t* input, uint32_t* output, size_t count) {{
    for (size_t i = 0; i < count; ++i) {{
        uint32_t in_val = input[i];
        uint32_t out_val = 0;

#if defined(__x86_64__) || defined(_M_X64) || defined(__i386__)
        __asm__ __volatile__(
            "movl %1, %%eax\\n\\t"
            "bswapl %%eax\\n\\t"
            "roll $13, %%eax\\n\\t"
            "xorl $0x{xor_key:X}, %%eax\\n\\t"
            "movl %%eax, %0\\n\\t"
            : "=r" (out_val)
            : "r" (in_val)
            : "%eax", "cc", "memory"
        );
#elif defined(__aarch64__)
        __asm__ __volatile__(
            "rev %w0, %w1\\n\\t"
            "ror %w0, %w0, #13\\n\\t"
            "eor %w0, %w0, #0x55AA\\n\\t"
            : "=r" (out_val)
            : "r" (in_val)
            : "memory"
        );
#else
        out_val = ((in_val >> 24) & 0xff) | ((in_val << 8) & 0xff0000) |
                  ((in_val >> 8) & 0xff00) | ((in_val << 24) & 0xff000000);
        out_val ^= 0x{xor_key:X};
#endif

        output[i] = out_val;
    }}
}}

int main() {{
    alignas(64) uint32_t src[16] = {{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16}};
    alignas(64) uint32_t dst[16] = {{0}};
    
    HardwareRegisterBlock regs = {{0, 0, 0, 0}};
    regs.CONTROL = 0x01;
    
    execute_asm_pipeline(src, dst, 16);
    
    regs.DATA_OUT = dst[0];
    regs.STATUS = 0x02;
    
    return (regs.STATUS == 0x02) ? 0 : 1;
}}
"""

    def generate_concurrency_edge_case(self) -> str:
        """Emits C++ code with atomics, relaxed memory order, and uninitialized memory storage."""
        slots_count = self.rng.choice([4, 8, 16])

        return f"""// Stress Category: Concurrency Edge Cases with Uninitialized Memory
#include <iostream>
#include <atomic>
#include <thread>
#include <vector>
#include <new>
#include <cstring>

struct ComplexPayload {{
    uint64_t id;
    double metrics[4];
    char flag_buffer[16];
}};

struct LockFreeQueueSlot {{
    std::atomic<bool> is_ready{{false}};
    alignas(alignof(ComplexPayload)) std::byte storage[sizeof(ComplexPayload)];
}};

void worker_produce(LockFreeQueueSlot& slot, uint64_t id) {{
    // Construct in-place in raw uninitialized storage
    ComplexPayload* payload = reinterpret_cast<ComplexPayload*>(slot.storage);
    payload->id = id;
    payload->metrics[0] = 3.14159 * static_cast<double>(id);
    payload->metrics[1] = 2.71828 * static_cast<double>(id);
    payload->metrics[2] = 1.41421 * static_cast<double>(id);
    payload->metrics[3] = 1.73205 * static_cast<double>(id);
    std::memset(payload->flag_buffer, 0x7F, sizeof(payload->flag_buffer));

    // Release fence ensures writes are visible before ready flag
    slot.is_ready.store(true, std::memory_order_release);
}}

bool worker_consume(LockFreeQueueSlot& slot, uint64_t expected_id) {{
    if (slot.is_ready.load(std::memory_order_acquire)) {{
        ComplexPayload* payload = reinterpret_cast<ComplexPayload*>(slot.storage);
        return payload->id == expected_id && payload->flag_buffer[0] == 0x7F;
    }}
    return false;
}}

int main() {{
    constexpr size_t NUM_SLOTS = {slots_count};
    LockFreeQueueSlot slots[NUM_SLOTS];

    for (size_t i = 0; i < NUM_SLOTS; ++i) {{
        worker_produce(slots[i], 1000 + i);
    }}

    bool all_valid = true;
    for (size_t i = 0; i < NUM_SLOTS; ++i) {{
        if (!worker_consume(slots[i], 1000 + i)) {{
            all_valid = false;
        }}
    }}

    return all_valid ? 0 : 1;
}}
"""

    def generate_loop_vectorizer_stress(self) -> str:
        """Emits non-unit stride loop iterations designed to stress auto-vectorization passes (Tree-SSA / IVOpts)."""
        stride = self.rng.choice([3, 5, 7])
        size = self.rng.choice([1024, 2048])

        return f"""// Stress Category: Loop Auto-Vectorizer & Tree-SSA Pass Stress
// Stresses SIMD widening and Induction Variable Optimization (IVOpts)
#include <iostream>
#include <vector>
#include <cmath>

#pragma GCC optimize("O3")

void execute_vector_stress(float* __restrict__ a, float* __restrict__ b, float* __restrict__ out, size_t n) {{
    // Multiple induction variables with non-unit strides and pointer aliasing hints
    #pragma GCC ivdep
    for (size_t i = 0; i < n - {stride}; i += {stride}) {{
        float temp1 = a[i] * b[i + 1] + 1.41421f;
        float temp2 = std::sqrt(std::abs(b[i] * a[i + 2])) + 2.71828f;
        out[i] = (temp1 > temp2) ? temp1 * 0.5f : temp2 * 1.5f;
        out[i + 1] = out[i] + a[i + 2];
    }}
}}

int main() {{
    constexpr size_t N = {size};
    alignas(64) float arr_a[N];
    alignas(64) float arr_b[N];
    alignas(64) float arr_out[N];

    for (size_t i = 0; i < N; ++i) {{
        arr_a[i] = static_cast<float>(i % 17) * 0.1f;
        arr_b[i] = static_cast<float>(i % 23) * 0.2f;
        arr_out[i] = 0.0f;
    }}

    execute_vector_stress(arr_a, arr_b, arr_out, N);
    return (arr_out[0] != 0.0f) ? 0 : 1;
}}
"""

    def generate_cpp20_concepts_stress(self) -> str:
        """Emits C++20 recursive concepts and requires-clause constraint satisfaction stress."""
        return """// Stress Category: C++20 Concepts & Nested Requires Constraints
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
"""

    def generate_deep_inliner_stress(self) -> str:
        """Emits deeply nested inline call chains and generic lambda closures to stress inliner tree depth."""
        return """// Stress Category: Deep Inliner Call Chains & Generic Lambdas
// Stresses GIMPLE inliner pass and devirtualization tree depth
#include <iostream>

#define ALWAYS_INLINE __attribute__((always_inline)) inline

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
    auto dispatcher = [](auto val, auto next_fn) ALWAYS_INLINE {
        return next_fn(val) + 1;
    };

    int result = dispatcher(42, [](int v) ALWAYS_INLINE {
        return stage_1(v);
    });

    return (result != 0) ? 0 : 1;
}
"""

    def generate_template_depth_overflow(self, depth: int = 1500) -> str:
        """Emits C++ code intentionally exceeding standard compiler recursion limits (-ftemplate-depth)."""
        return f"""// Stress Category: Exceeded Template Recursion Depth Limit
// Provokes compiler frontend depth cutoff (default max 900)
#include <iostream>

template <int N>
struct RecursiveLimitStress {{
    static constexpr int val = 1 + RecursiveLimitStress<N - 1>::val;
}};

template <>
struct RecursiveLimitStress<0> {{
    static constexpr int val = 0;
}};

int main() {{
    // Depth {depth} intentionally exceeds GCC default depth limit of 900
    constexpr int result = RecursiveLimitStress<{depth}>::val;
    return result;
}}
"""

    def generate_inline_asm_register_exhaustion(self) -> str:
        """Emits inline assembly with clobber constraints exceeding available general-purpose registers."""
        return """// Stress Category: Inline Assembly Register Allocator Exhaustion
// Provokes backend impossible reload / register spill failure
#include <cstdint>

int main() {
    uint32_t r0 = 1, r1 = 2, r2 = 3, r3 = 4, r4 = 5;
    uint32_t r5 = 6, r6 = 7, r7 = 8, r8 = 9, r9 = 10;
    uint32_t r10 = 11, r11 = 12, r12 = 13, r13 = 14, r14 = 15;

#if defined(__x86_64__) || defined(_M_X64)
    __asm__ __volatile__(
        "nop\\n"
        : "+r"(r0), "+r"(r1), "+r"(r2), "+r"(r3), "+r"(r4),
          "+r"(r5), "+r"(r6), "+r"(r7), "+r"(r8), "+r"(r9),
          "+r"(r10), "+r"(r11), "+r"(r12), "+r"(r13), "+r"(r14)
        :
        : "rax", "rbx", "rcx", "rdx", "rsi", "rdi", "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15", "memory"
    );
#else
    __asm__ __volatile__(
        "nop\\n"
        : "+r"(r0), "+r"(r1), "+r"(r2), "+r"(r3), "+r"(r4)
        :
        : "r0", "r1", "r2", "r3", "r4", "r5", "r6", "r7", "memory"
    );
#endif

    return static_cast<int>(r0 + r14);
}
"""

    def generate_ambiguous_template_overload(self) -> str:
        """Emits conflicting SFINAE candidate templates to stress overload resolution."""
        return """// Stress Category: Ambiguous SFINAE Overload Conflict
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
"""

    def generate_constexpr_step_limit_violation(self) -> str:
        """Emits constexpr evaluation exceeding compile-time loop evaluation step quota."""
        return """// Stress Category: Constexpr Step Limit Exhaustion
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
"""

    def generate_cpp20_concept_cycle_violation(self) -> str:
        """Emits mutually recursive concept constraints to stress frontend dependency cycles."""
        return """// Stress Category: Recursive Concept Dependency Cycle
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
"""

    def generate_suite_with_metadata(
        self,
        output_dir: str = "compiler_tests",
        count: int = 4,
        mode: str = "balanced",
    ) -> List[TestMetadata]:
        """Dynamically emits C++ source files and returns rich metadata for each test case.

        Args:
            output_dir: Destination folder path for generated .cpp test files.
            count: Number of test files to emit.
            mode: 'valid-only' | 'balanced' | 'aggressive'

        Returns:
            List of TestMetadata objects describing the generated test suite.
        """
        os.makedirs(output_dir, exist_ok=True)

        valid_entries: List[Tuple[str, str, str, str, str, Any]] = [
            (
                "valid_template_recursion",
                "Frontend Parser / Template Metaprogramming",
                "Template Instantiation Pass",
                "PASS",
                "-O3 -std=c++20",
                lambda i: self.generate_template_recursion(depth=300 + (i * 50)),
            ),
            (
                "valid_pointer_aliasing",
                "Strict Aliasing / Pointer Arithmetic",
                "Tree-SSA SCCVN Pass",
                "PASS",
                "-O3 -fstrict-aliasing",
                lambda i: self.generate_pointer_aliasing(dimensions=8 + (i * 4)),
            ),
            (
                "valid_inline_asm",
                "Register Allocator / Inline Assembly",
                "Backend Instruction Selection",
                "PASS",
                "-O3",
                lambda i: self.generate_inline_asm_volatile(),
            ),
            (
                "valid_concurrency_atomic",
                "Atomic Memory / Concurrency Lowering",
                "SelectionDAG Atomic Lowering",
                "PASS",
                "-O3 -std=c++20",
                lambda i: self.generate_concurrency_edge_case(),
            ),
            (
                "valid_vectorizer_stress",
                "Loop Auto-Vectorizer / Tree-SSA",
                "LoopVectorizePass / IVOpts",
                "PASS",
                "-O3 -ftree-vectorize",
                lambda i: self.generate_loop_vectorizer_stress(),
            ),
            (
                "valid_cpp20_concepts",
                "Frontend Parser / C++20 Concepts",
                "Constraint Satisfaction Evaluator",
                "PASS",
                "-O3 -std=c++20",
                lambda i: self.generate_cpp20_concepts_stress(),
            ),
            (
                "valid_deep_inliner",
                "Dead Code Elimination / Function Inliner",
                "GIMPLE Inliner Pass",
                "PASS",
                "-O3 -finline-functions",
                lambda i: self.generate_deep_inliner_stress(),
            ),
        ]

        edge_entries: List[Tuple[str, str, str, str, str, Any]] = [
            (
                "edge_depth_overflow",
                "Frontend Parser / Template Substitution",
                "Template Depth Cutoff",
                "COMPILE_ERROR",
                "-O3 -std=c++20",
                lambda i: self.generate_template_depth_overflow(depth=1500),
            ),
            (
                "edge_asm_reg_exhaustion",
                "Register Allocator / Inline Assembly",
                "Greedy Register Allocator Reload",
                "COMPILE_ERROR",
                "-O3",
                lambda i: self.generate_inline_asm_register_exhaustion(),
            ),
            (
                "edge_ambiguous_sfinae",
                "Frontend Parser / Overload Resolution",
                "Template Overload Disambiguation",
                "COMPILE_ERROR",
                "-O3 -std=c++17",
                lambda i: self.generate_ambiguous_template_overload(),
            ),
            (
                "edge_constexpr_limit",
                "Frontend Parser / Constexpr Evaluation",
                "Constexpr Step Interpreter",
                "COMPILE_ERROR",
                "-O3 -std=c++20",
                lambda i: self.generate_constexpr_step_limit_violation(),
            ),
            (
                "edge_concept_cycle",
                "Frontend Parser / C++20 Concepts",
                "Concept Constraint Verification",
                "COMPILE_ERROR",
                "-O3 -std=c++20",
                lambda i: self.generate_cpp20_concept_cycle_violation(),
            ),
        ]

        if mode == "valid-only":
            pool = valid_entries
        elif mode == "aggressive":
            pool = edge_entries + [valid_entries[0]]
        else:  # balanced
            pool = []
            max_len = max(len(valid_entries), len(edge_entries))
            for i in range(max_len):
                if i < len(valid_entries):
                    pool.append(valid_entries[i])
                if i < len(edge_entries):
                    pool.append(edge_entries[i])

        metadata_list: List[TestMetadata] = []
        for idx in range(count):
            name, cat, pass_name, expected, flags, gen_fn = pool[idx % len(pool)]
            code = gen_fn(idx)
            filename = f"test_{idx+1:03d}_{name}.cpp"
            filepath = os.path.join(output_dir, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code)

            meta = TestMetadata(
                filepath=filepath,
                category=cat,
                target_pass=pass_name,
                expected_outcome=expected,
                compiler_flags=flags,
                description=f"Generated synthetic stress test {filename} targeting {cat} ({pass_name}).",
            )
            metadata_list.append(meta)

        return metadata_list

    def generate_suite(
        self,
        output_dir: str = "compiler_tests",
        count: int = 4,
        mode: str = "balanced",
    ) -> List[str]:
        """Dynamically emits C++ source files targeting compiler stress areas.

        (Backward compatible: returns list of file paths)
        """
        metadata = self.generate_suite_with_metadata(output_dir=output_dir, count=count, mode=mode)
        return [m.filepath for m in metadata]


if __name__ == "__main__":
    generator = CompilerTestGenerator()
    suite = generator.generate_suite_with_metadata("compiler_tests", 6, mode="balanced")
    print(f"Generated {len(suite)} stress tests with metadata:")
    for item in suite:
        print(f"  [{item.expected_outcome}] {item.filepath} -> {item.category} ({item.target_pass})")
