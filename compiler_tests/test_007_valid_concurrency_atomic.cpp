// Stress Category: Concurrency Edge Cases with Uninitialized Memory
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
