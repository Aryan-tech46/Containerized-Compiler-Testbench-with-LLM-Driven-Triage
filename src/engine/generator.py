"""Compiler Test Generator module.

Generates syntactically valid yet highly complex C++ source files targeting
known compiler stress areas:
1. Deep template metaprogramming recursion
2. Complex pointer arithmetic and aliasing
3. Heavy inline assembly and volatile memory manipulation
4. Concurrency edge cases with uninitialized memory
"""

import os
import random
from pathlib import Path
from typing import List, Optional


class CompilerTestGenerator:
    """Generates synthetic C++ edge-case source files designed to stress compilers."""

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)

    def generate_template_recursion(self, depth: int = 450) -> str:
        """Emits C++ source code with deep template recursion and SFINAE type lists."""
        return f"""// Stress Category: Deep Template Metaprogramming Recursion
// Target Depth: {depth}
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
    constexpr int compute() const {{
        return Depth + Sub::compute();
    }}
}};

template <>
struct DeepTemplateChain<0> {{
    constexpr int compute() const {{
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
    volatile int res = chain.compute();
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
        u_ptr->u64[i] = 0xDEADBEEFCAFEBABEULL ^ (i * 0x101010101010101ULL);
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
        return """// Stress Category: Heavy Inline Assembly and Volatile Memory Manipulation
#include <iostream>
#include <cstdint>

// Volatile hardware register emulation
struct HardwareRegisterBlock {
    volatile uint32_t CONTROL;
    volatile uint32_t STATUS;
    volatile uint32_t DATA_IN;
    volatile uint32_t DATA_OUT;
};

void execute_asm_pipeline(uint32_t* input, uint32_t* output, size_t count) {
    for (size_t i = 0; i < count; ++i) {
        uint32_t in_val = input[i];
        uint32_t out_val = 0;

#if defined(__x86_64__) || defined(_M_X64) || defined(__i386__)
        __asm__ __volatile__(
            "movl %1, %%eax\\n\\t"
            "bswapl %%eax\\n\\t"
            "roll $13, %%eax\\n\\t"
            "xorl $0x55AA55AA, %%eax\\n\\t"
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
        out_val ^= 0x55AA55AA;
#endif

        output[i] = out_val;
    }
}

int main() {
    alignas(64) uint32_t src[16] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16};
    alignas(64) uint32_t dst[16] = {0};
    
    HardwareRegisterBlock regs = {0, 0, 0, 0};
    regs.CONTROL = 0x01;
    
    execute_asm_pipeline(src, dst, 16);
    
    regs.DATA_OUT = dst[0];
    regs.STATUS = 0x02;
    
    return (regs.STATUS == 0x02) ? 0 : 1;
}
"""

    def generate_concurrency_edge_case(self) -> str:
        """Emits C++ code with atomics, relaxed memory order, and uninitialized memory storage."""
        return """// Stress Category: Concurrency Edge Cases with Uninitialized Memory
#include <iostream>
#include <atomic>
#include <thread>
#include <vector>
#include <new>
#include <cstring>

struct ComplexPayload {
    uint64_t id;
    double metrics[4];
    char flag_buffer[16];
};

struct LockFreeQueueSlot {
    std::atomic<bool> is_ready{false};
    alignas(alignof(ComplexPayload)) std::byte storage[sizeof(ComplexPayload)];
};

void worker_produce(LockFreeQueueSlot& slot, uint64_t id) {
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
}

bool worker_consume(LockFreeQueueSlot& slot, uint64_t expected_id) {
    if (slot.is_ready.load(std::memory_order_acquire)) {
        ComplexPayload* payload = reinterpret_cast<ComplexPayload*>(slot.storage);
        return payload->id == expected_id && payload->flag_buffer[0] == 0x7F;
    }
    return false;
}

int main() {
    constexpr size_t NUM_SLOTS = 8;
    LockFreeQueueSlot slots[NUM_SLOTS];

    for (size_t i = 0; i < NUM_SLOTS; ++i) {
        worker_produce(slots[i], 1000 + i);
    }

    bool all_valid = true;
    for (size_t i = 0; i < NUM_SLOTS; ++i) {
        if (!worker_consume(slots[i], 1000 + i)) {
            all_valid = false;
        }
    }

    return all_valid ? 0 : 1;
}
"""

    def generate_suite(self, output_dir: str = "compiler_tests", count: int = 4) -> List[str]:
        """Dynamically emits valid yet complex C++ source files targeting compiler stress areas.

        Args:
            output_dir: Destination folder path for generated .cpp test files.
            count: Number of test files to emit.

        Returns:
            List of generated test file paths.
        """
        os.makedirs(output_dir, exist_ok=True)
        generators = [
            ("template_recursion", lambda i: self.generate_template_recursion(depth=300 + (i * 50))),
            ("pointer_aliasing", lambda i: self.generate_pointer_aliasing(dimensions=8 + (i * 4))),
            ("inline_asm_volatile", lambda i: self.generate_inline_asm_volatile()),
            ("concurrency_edge_case", lambda i: self.generate_concurrency_edge_case()),
        ]

        generated_files: List[str] = []
        for idx in range(count):
            name, gen_func = generators[idx % len(generators)]
            code = gen_func(idx)
            filename = f"test_{idx+1:03d}_{name}.cpp"
            filepath = os.path.join(output_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code)
            generated_files.append(filepath)

        return generated_files


if __name__ == "__main__":
    generator = CompilerTestGenerator()
    suite = generator.generate_suite("compiler_tests", 4)
    print(f"Generated {len(suite)} test files:")
    for path in suite:
        print(f"  - {path}")
