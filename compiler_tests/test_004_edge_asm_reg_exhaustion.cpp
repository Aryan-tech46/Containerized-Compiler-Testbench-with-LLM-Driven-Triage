// Stress Category: Inline Assembly Register Allocator Exhaustion
// Provokes backend impossible reload / register spill failure
#include <cstdint>

int main() {
    uint32_t r0 = 1, r1 = 2, r2 = 3, r3 = 4, r4 = 5;
    uint32_t r5 = 6, r6 = 7, r7 = 8, r8 = 9, r9 = 10;
    uint32_t r10 = 11, r11 = 12, r12 = 13, r13 = 14, r14 = 15;

#if defined(__x86_64__) || defined(_M_X64)
    __asm__ __volatile__(
        "nop\n"
        : "+r"(r0), "+r"(r1), "+r"(r2), "+r"(r3), "+r"(r4),
          "+r"(r5), "+r"(r6), "+r"(r7), "+r"(r8), "+r"(r9),
          "+r"(r10), "+r"(r11), "+r"(r12), "+r"(r13), "+r"(r14)
        :
        : "rax", "rbx", "rcx", "rdx", "rsi", "rdi", "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15", "memory"
    );
#else
    __asm__ __volatile__(
        "nop\n"
        : "+r"(r0), "+r"(r1), "+r"(r2), "+r"(r3), "+r"(r4)
        :
        : "r0", "r1", "r2", "r3", "r4", "r5", "r6", "r7", "memory"
    );
#endif

    return static_cast<int>(r0 + r14);
}
