// Stress Category: Complex Pointer Arithmetic and Aliasing
#include <iostream>
#include <cstdint>
#include <cstring>
#include <vector>

union AliasingUnion {
    uint64_t u64[4];
    uint32_t u32[8];
    uint8_t  u8[32];
    double   d64[4];
};

// Complex pointer stepping through multidimensional array decay
void stress_aliasing(volatile char* buffer, size_t len) {
    uintptr_t raw_addr = reinterpret_cast<uintptr_t>(buffer);
    uintptr_t aligned_addr = (raw_addr + 31) & ~static_cast<uintptr_t>(31);
    
    AliasingUnion* u_ptr = reinterpret_cast<AliasingUnion*>(aligned_addr);
    
    for (size_t i = 0; i < 4; ++i) {
        u_ptr->u64[i] = 0xDEADBEEFCAFEBABEULL ^ (i * 0x101010101010101ULL);
    }
    
    // Strict aliasing stress: pointer reinterpretation across types
    uint32_t* p32 = reinterpret_cast<uint32_t*>(u_ptr->u8 + 7);
    volatile uint32_t read_val = *p32;
    *p32 = read_val ^ 0xAAAA5555;
    
    // Multidimensional offset folding
    int32_t matrix[12][12];
    int32_t* base = &matrix[0][0];
    for (int r = 0; r < 12; ++r) {
        for (int c = 0; c < 12; ++c) {
            ptrdiff_t offset = (r * 12) + c;
            *(base + offset) = (r ^ c) + static_cast<int32_t>(read_val);
        }
    }
}

int main() {
    alignas(64) char raw_buffer[512];
    std::memset(raw_buffer, 0x5A, sizeof(raw_buffer));
    stress_aliasing(raw_buffer, sizeof(raw_buffer));
    return 0;
}
