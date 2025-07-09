#ifdef OMPGPU

#define GPU_DATA_ALLOC(...) !$omp target data map(alloc: __VA_ARGS__)
#define GPU_DATA_PRESENT_SIMPLE(...) !$omp target enter data map(present: __VA_ARGS__)
#define GPU_DATA_PRESENT_IF(condition_arg, ...) !$omp target enter data if(condition_arg) map(present: __VA_ARGS__)
#define GPU_DATA_PRESENT_COPY(condition_arg, copyin_arg, copy_arg, ...) !$omp target enter data if(condition_arg) map(present: __VA_ARGS__) map(to: copyin_arg) map(tofrom: copy_arg)

#else

#define GPU_DATA_ALLOC(...) !$acc enter data create(__VA_ARGS__)
#define GPU_DATA_PRESENT_SIMPLE(...) !$acc data present(__VA_ARGS__)
#define GPU_DATA_PRESENT_IF(condition_arg, ...) !$acc data present(__VA_ARGS__) if(condition_arg)
#define GPU_DATA_PRESENT_COPY(condition_arg, copyin_arg, copy_arg, ...) !$acc data present(__VA_ARGS__) copyin(copyin_arg) copy(copy_arg) if(condition_arg)

#endif
