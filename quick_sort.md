# 快速排序 (Quick Sort)

## 算法简介

快速排序是一种高效的**分治**排序算法。其核心思想是：

1. 选择一个**基准元素 (pivot)**
2. 将数组分为两部分：小于基准的元素放在左边，大于基准的元素放在右边
3. 递归地对左右两部分继续排序

## 代码实现 (Python)

```python
def quick_sort(arr):
    """
    快速排序 - 简洁版
    时间复杂度: O(n log n) 平均 / O(n^2) 最坏
    空间复杂度: O(log n)
    """
    if len(arr) <= 1:
        return arr
    
    pivot = arr[len(arr) // 2]  # 选择中间元素作为基准
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    
    return quick_sort(left) + middle + quick_sort(right)


def quick_sort_inplace(arr, low=0, high=None):
    """
    快速排序 - 原地排序版本（更节省空间）
    """
    if high is None:
        high = len(arr) - 1
    
    if low < high:
        pivot_index = partition(arr, low, high)
        quick_sort_inplace(arr, low, pivot_index - 1)
        quick_sort_inplace(arr, pivot_index + 1, high)
    
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
```

## 使用示例

```python
# 测试
if __name__ == "__main__":
    # 简洁版
    arr1 = [64, 34, 25, 12, 22, 11, 90]
    print("原始数组:", arr1)
    print("排序后:", quick_sort(arr1))
    
    # 原地排序版
    arr2 = [64, 34, 25, 12, 22, 11, 90]
    quick_sort_inplace(arr2)
    print("原地排序:", arr2)
```

## 复杂度分析

| 指标 | 最好情况 | 平均情况 | 最坏情况 |
|------|----------|----------|----------|
| 时间复杂度 | O(n log n) | O(n log n) | O(n²) |
| 空间复杂度 | O(log n) | O(log n) | O(n) |
| 稳定性 | 不稳定 | 不稳定 | 不稳定 |

## 算法步骤图示

```
初始: [64, 34, 25, 12, 22, 11, 90]
         pivot=22

分区: [12, 11]  [22]  [64, 34, 25, 90]
       递归排序   |      递归排序

结果: [11, 12, 22, 25, 34, 64, 90]
```

## 优化建议

1. **基准选择**: 使用三数取中法（首、中、尾的中位数）避免最坏情况
2. **小数组优化**: 当子数组长度小于阈值时，切换到插入排序
3. **尾递归优化**: 先处理较短的子数组，减少栈深度
