"""
快速排序算法实现 (Quick Sort)
==============================
快速排序是一种高效的排序算法，采用分治法策略。

时间复杂度：
- 平均情况：O(n log n)
- 最坏情况：O(n^2)
- 最好情况：O(n log n)

空间复杂度：O(log n)（递归调用栈）
"""


def quick_sort(arr: list) -> list:
    """
    快速排序主函数
    
    参数:
        arr: 待排序的列表
    
    返回:
        排序后的新列表
    """
    if len(arr) <= 1:
        return arr
    
    # 选择中间元素作为基准
    pivot = arr[len(arr) // 2]
    
    # 分割数组
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    
    # 递归排序并合并
    return quick_sort(left) + middle + quick_sort(right)


def quick_sort_inplace(arr: list, low: int = 0, high: int = None) -> None:
    """
    原地快速排序（空间优化版本）
    
    参数:
        arr: 待排序的列表（会被修改）
        low: 起始索引
        high: 结束索引
    """
    if high is None:
        high = len(arr) - 1
    
    if low < high:
        # 获取分区点
        pi = partition(arr, low, high)
        
        # 递归排序左右两部分
        quick_sort_inplace(arr, low, pi - 1)
        quick_sort_inplace(arr, pi + 1, high)


def partition(arr: list, low: int, high: int) -> int:
    """
    分区函数
    
    参数:
        arr: 待分区的列表
        low: 起始索引
        high: 结束索引
    
    返回:
        基准元素的最终位置
    """
    # 选择最后一个元素作为基准
    pivot = arr[high]
    i = low - 1  # 较小元素的索引
    
    for j in range(low, high):
        if arr[j] <= pivot:
            i += 1
            arr[i], arr[j] = arr[j], arr[i]
    
    # 将基准元素放到正确位置
    arr[i + 1], arr[high] = arr[high], arr[i + 1]
    return i + 1


# ===== 测试代码 =====
if __name__ == "__main__":
    import random
    
    # 测试用例 1：普通数组
    print("测试 1 - 普通数组:")
    test_arr1 = [64, 34, 25, 12, 22, 11, 90]
    print(f"  原始: {test_arr1}")
    print(f"  排序: {quick_sort(test_arr1)}")
    
    # 测试用例 2：包含重复元素
    print("\n测试 2 - 包含重复元素:")
    test_arr2 = [5, 2, 8, 2, 9, 5, 1, 8]
    print(f"  原始: {test_arr2}")
    print(f"  排序: {quick_sort(test_arr2)}")
    
    # 测试用例 3：原地排序
    print("\n测试 3 - 原地排序:")
    test_arr3 = [3, 6, 8, 10, 1, 2, 1]
    print(f"  原始: {test_arr3}")
    quick_sort_inplace(test_arr3)
    print(f"  排序: {test_arr3}")
    
    # 测试用例 4：随机大数组
    print("\n测试 4 - 随机大数组 (20个元素):")
    test_arr4 = [random.randint(1, 100) for _ in range(20)]
    print(f"  原始: {test_arr4}")
    print(f"  排序: {quick_sort(test_arr4)}")
    
    # 测试用例 5：已排序数组
    print("\n测试 5 - 已排序数组:")
    test_arr5 = [1, 2, 3, 4, 5]
    print(f"  原始: {test_arr5}")
    print(f"  排序: {quick_sort(test_arr5)}")
    
    # 测试用例 6：逆序数组
    print("\n测试 6 - 逆序数组:")
    test_arr6 = [5, 4, 3, 2, 1]
    print(f"  原始: {test_arr6}")
    print(f"  排序: {quick_sort(test_arr6)}")
