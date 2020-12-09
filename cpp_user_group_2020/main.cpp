#include <iostream>
#include <iomanip>
#include <memory>
#include <ctime>
#include <cstdint>


template <typename T>
__attribute__((__noinline__)) T sum(const T * ptr, const T * end)
{
    T res{};
    while (ptr < end)
    {
        res += *ptr;
        ++ptr;
    }
    return res;
}

uint64_t nanoseconds()
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return uint64_t(ts.tv_sec * 1000000000LL + ts.tv_nsec);
}

int main(int, char **)
{
    using T = double;
    constexpr size_t size = 1000000000;

    std::unique_ptr<T[]> arr(new T[size]);
    for (size_t i = 0; i < size; ++i)
        arr[i] = i;

    auto ns = nanoseconds();
    T res = sum(arr.get(), arr.get() + size);
    ns = nanoseconds() - ns;

    std::cout << std::fixed << std::setprecision(3) << "Res: " << res << ", time: " << ns / 1e9 << ", " << static_cast<double>(sizeof(T) * size) / ns << " GB/sec." << '\n';
    return 0;
}
