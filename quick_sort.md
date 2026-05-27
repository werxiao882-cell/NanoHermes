# 快速排序算法 (Quick Sort)

## 1. 算法简介

快速排序是一种高效的排序算法，采用**分治法（Divide and Conquer）**策略。

- **平均时间复杂度**: O(n log n)
- **最坏时间复杂度**: O(n²)（已排序数组且选择最左/最右为基准时）
- **空间复杂度**: O(log n)（递归调用栈）
- **稳定性**: 不稳定排序

## 2. 算法原理

1. **选择基准（Pivot）**: 从数组中选择一个元素作为基准
2. **分区（Partition）**: 将数组分为两部分，小于基准的放左边，大于基准的放右边
3. **递归排序**: 对左右两部分分别递归应用快速排序

## 3. Python 实现

### 3.1 标准实现

```python
def quick_sort(arr):
    """快速排序 - 标准实现"""
    if len(arr) <= 1:
        return arr
    
    pivot = arr[len(arr) // 2]  # 选择中间元素作为基准
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    
    return quick_sort(left) + middle + quick_sort(right)


# 测试
arr = [64, 34, 25, 12, 22, 11, 90]
sorted_arr = quick_sort(arr)
print(f"原数组: {arr}")
print(f"排序后: {sorted_arr}")
```

### 3.2 原地排序实现（更节省空间）

```python
def quick_sort_inplace(arr, low=0, high=None):
    """快速排序 - 原地排序版本"""
    if high is None:
        high = len(arr) - 1
    
    if low < high:
        pi = partition(arr, low, high)
        quick_sort_inplace(arr, low, pi - 1)
        quick_sort_inplace(arr, pi + 1, high)
    
    return arr


def partition(arr, low, high):
    """分区函数"""
    pivot = arr[high]  # 选择最后一个元素作为基准
    i = low - 1
    
    for j in range(low, high):
        if arr[j] <= pivot:
            i += 1
            arr[i], arr[j] = arr[j], arr[i]
    
    arr[i + 1], arr[high] = arr[high], arr[i + 1]
    return i + 1


# 测试
arr = [64, 34, 25, 12, 22, 11, 90]
print(f"原地排序前: {arr}")
quick_sort_inplace(arr)
print(f"原地排序后: {arr}")
```

### 3.3 可视化执行过程

```python
def quick_sort_verbose(arr, depth=0):
    """带日志的快速排序"""
    indent = "  " * depth
    
    if len(arr) <= 1:
        return arr
    
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    
    print(f"{indent}基准: {pivot}")
    print(f"{indent}左边: {left}")
    print(f"{indent}右边: {right}")
    
    sorted_left = quick_sort_verbose(left, depth + 1)
    sorted_right = quick_sort_verbose(right, depth + 1)
    
    result = sorted_left + middle + sorted_right
    print(f"{indent}合并: {result}")
    return result


# 测试
print("=== 快速排序执行过程 ===")
arr = [3, 6, 8, 10, 1, 2, 1]
quick_sort_verbose(arr)
```

## 4. 算法执行示例

以数组 `[3, 6, 8, 10, 1, 2, 1]` 为例：

```
原始数组: [3, 6, 8, 10, 1, 2, 1]
基准: 10 → 左: [3, 6, 8, 1, 2, 1] | 右: []
基准: 1 → 左: [] | 右: [3, 6, 8, 2]
基准: 6 → 左: [3, 2] | 右: [8]
...
最终结果: [1, 1, 2, 3, 6, 8, 10]
```

## 5. 优化技巧

### 5.1 三数取中法选择基准

```python
def median_of_three(arr, low, high):
    """三数取中法选择基准"""
    mid = (low + high) // 2
    if arr[low] > arr[mid]:
        arr[low], arr[mid] = arr[mid], arr[low]
    if arr[low] > arr[high]:
        arr[low], arr[high] = arr[high], arr[low]
    if arr[mid] > arr[high]:
        arr[mid], arr[high] = arr[high], arr[mid]
    return mid
```

### 5.2 小数组使用插入排序

```python
def quick_sort_optimized(arr, low=0, high=None):
    """优化的快速排序"""
    if high is None:
        high = len(arr) - 1
    
    # 小数组使用插入排序
    if high - low < 10:
        insertion_sort(arr, low, high)
        return arr
    
    if low < high:
        pi = partition(arr, low, high)
        quick_sort_optimized(arr, low, pi - 1)
        quick_sort_optimized(arr, pi + 1, high)
    
    return arr


def insertion_sort(arr, low, high):
    """插入排序"""
    for i in range(low + 1, high + 1):
        key = arr[i]
        j = i - 1
        while j >= low and arr[j] > key:
            arr[j + 1] = arr[j]
            j -= 1
        arr[j + 1] = key
```

## 6. 与其他排序算法比较

| 算法 | 平均时间 | 最坏时间 | 空间 | 稳定性 |
|------|---------|---------|------|--------|
| 快速排序 | O(n log n) | O(n²) | O(log n) | ❌ |
| 归并排序 | O(n log n) | O(n log n) | O(n) | ✅ |
| 堆排序 | O(n log n) | O(n log n) | O(1) | ❌ |
| 冒泡排序 | O(n²) | O(n²) | O(1) | ✅ |

## 7. 使用场景

✅ **适合**:
- 一般情况下的排序需求
- 内存受限的场景（原地排序版本）
- 数据随机分布时

❌ **不适合**:
- 需要稳定排序的场景
- 数据已基本有序时（可能退化到 O(n²)）
- 链表排序（归并排序更合适）
