# Wan2.1 深度架构分析

> 基于 Wan-Video/Wan2.1 源码的深度技术分析
> 文档生成时间：2026年6月
> 源码版本：GitHub commit 9737cba

---

## 一、整体架构总览 — 三大核心组件

Wan2.1 是一个**基于 DiT（Diffusion Transformer）的视频生成模型**，其核心架构由三大组件组成：

```
┌─────────────────────────────────────────────────────────────┐
│                      Wan2.1 推理流程                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │  T5-XXL      │    │  Wan-VAE     │    │   Wan DiT     │  │
│  │  文本编码器   │    │  视频编解码器 │    │   主干网络     │  │
│  │              │    │              │    │               │  │
│  │  Text →      │    │  Video ↔     │    │  Noise +      │  │
│  │  Embeddings  │    │  Latent      │    │  Condition →  │  │
│  │  (4096-d)    │    │  (4,8,8)     │    │  Video Latent │  │
│  └──────┬───────┘    └──────┬───────┘    └───────┬───────┘  │
│         │                   │                    │          │
│         ▼                   ▼                    ▼          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                 Flow Matching 采样                     │   │
│  │         (t=1.0 纯噪声 → t=0.0 干净潜变量)              │   │
│  └──────────────────────────────────────────────────────┘   │
│                              │                              │
│                              ▼                              │
│                    ┌─────────────────┐                      │
│                    │   VAE Decoder   │                      │
│                    │   Latent→Video  │                      │
│                    └─────────────────┘                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.1 三大组件职责

| 组件 | 源码位置 | 职责 | 关键参数 |
|------|----------|------|----------|
| **T5-XXL 编码器** | `wan/modules/t5.py` | 文本→4096维语义嵌入 | `umt5-xxl`, 512 tokens |
| **Wan-VAE** | `wan/modules/vae.py` | 视频↔潜变量编解码 | 压缩比 (4,8,8) |
| **Wan DiT** | `wan/modules/model.py` | 核心生成网络 | 40 layers, 5120 dim (14B) |

### 1.2 模型变体

| 变体 | 参数量 | hidden_dim | heads | layers | 最低显存 |
|------|--------|------------|-------|--------|----------|
| T2V-1.3B | 1.3B | 1536 | 12 | 30 | 8.19 GB |
| T2V-14B | 14B | 5120 | 40 | 40 | 80+ GB |
| I2V-14B | 14B | 5120 | 40 | 40 | 80+ GB |
| FLF2V-14B | 14B | 5120 | 40 | 40 | 80+ GB |

---

## 二、DiT 主干网络详解 — Patch Embedding、WanAttentionBlock、3D RoPE、AdaLN-Zero

### 2.1 Patch Embedding — 视频到序列的转换

Wan2.1 使用 **3D 卷积** 将视频切分为 patch 序列：

```python
# model.py line 456-457
self.patch_embedding = nn.Conv3d(
    in_dim, dim, kernel_size=patch_size, stride=patch_size
)
# patch_size = (1, 2, 2)  — 时间1帧, 空间2×2像素
```

**Tensor Shape 变化：**

```
输入视频: [C_in=16, F, H, W]
         ↓ Conv3d kernel=(1,2,2), stride=(1,2,2)
Patch:    [dim, F, H/2, W/2]
         ↓ flatten + transpose
序列:     [F * H/2 * W/2, dim]
```

**关键设计：**
- 时间维度 patch_size=1，**不压缩时间**，保留每一帧的时序信息
- 空间维度 patch_size=2，**4 倍空间压缩**，减少 token 数量
- 14B 模型 `in_dim=16`（VAE 输出的潜变量通道数）

### 2.2 WanAttentionBlock — 核心 Transformer 块

每个 `WanAttentionBlock` 包含：

```python
# model.py line 238-317
class WanAttentionBlock(nn.Module):
    def __init__(self, cross_attn_type, dim, ffn_dim, num_heads, ...):
        # 归一化层
        self.norm1 = WanLayerNorm(dim, eps)       # Self-Attention 前
        self.norm2 = WanLayerNorm(dim, eps)       # FFN 前
        self.norm3 = WanLayerNorm(dim, eps, elementwise_affine=True)  # Cross-Attention 前
        
        # 注意力层
        self.self_attn = WanSelfAttention(dim, num_heads, window_size, qk_norm, eps)
        self.cross_attn = WAN_CROSSATTENTION_CLASSES[cross_attn_type](...)
        
        # 前馈网络
        self.ffn = nn.Sequential(
            nn.Linear(dim, ffn_dim),
            nn.GELU(approximate='tanh'),  # GELU 近似 tanh 版本
            nn.Linear(ffn_dim, dim)
        )
        
        # AdaLN 调制参数 (6 个: shift/scale/gate × 2)
        self.modulation = nn.Parameter(torch.randn(1, 6, dim) / dim**0.5)
```

**Block 内部数据流：**

```
x → norm1 × (1+e[1]) + e[0]  ─→ Self-Attention  ─→ x + y * e[2]
                                                        ↓
x → norm3                       ─→ Cross-Attention ─→ x + cross_attn_out
                                                        ↓
x → norm2 × (1+e[4]) + e[3]  ─→ FFN              ─→ x + y * e[5]
                                                        ↓
                                                    输出
```

其中 `e` 是来自时间嵌入的调制参数，将时间条件注入到每个 Transformer 层。

### 2.3 3D RoPE — 三维旋转位置编码

Wan2.1 的 RoPE 同时编码**时间、高度、宽度**三个维度：

```python
# model.py line 32-70
@amp.autocast(enabled=False)
def rope_params(max_seq_len, dim, theta=10000):
    # 生成一维频率: theta = 10000
    freqs = torch.outer(
        torch.arange(max_seq_len),
        1.0 / torch.pow(theta, torch.arange(0, dim, 2).to(torch.float64).div(dim))
    )
    freqs = torch.polar(torch.ones_like(freqs), freqs)  # 转为复数
    return freqs

@amp.autocast(enabled=False)
def rope_apply(x, grid_sizes, freqs):
    # RoPE 频率分为三部分: 时间/高度/宽度
    n, c = x.size(2), x.size(3) // 2
    freqs = freqs.split([c - 2*(c//3), c//3, c//3], dim=1)
    # 按视频尺寸 (F, H, W) 分别扩展频率，然后复数乘法
    for i, (f, h, w) in enumerate(grid_sizes.tolist()):
        freqs_i = torch.cat([
            freqs[0][:f].view(f, 1, 1, -1).expand(f, h, w, -1),  # 时间
            freqs[1][:h].view(1, h, 1, -1).expand(f, h, w, -1),  # 高度
            freqs[2][:w].view(1, 1, w, -1).expand(f, h, w, -1),  # 宽度
        ], dim=-1).reshape(seq_len, 1, -1)
        x_i = torch.view_as_real(x_i * freqs_i).flatten(2)  # 复数乘法 = 旋转
```

**频率分配比例（以 head_dim=128 为例）：**
- 时间维度：`128 - 2*(128//6) = 128 - 42 = 86` 维（约 67%）
- 高度维度：`2 * (128//6) = 42` 维（约 17%）
- 宽度维度：`2 * (128//6) = 42` 维（约 17%）

**为什么时间维度占比最大？** 视频的时序关系比空间关系更复杂，需要更多频率分量来编码运动轨迹。

### 2.4 AdaLN-Zero — 自适应层归一化

Wan2.1 使用 **AdaLN-Zero** 变体，将时间条件注入每个 Block：

```python
# model.py line 296-316
def forward(self, x, e, seq_lens, grid_sizes, freqs, context, context_lens):
    # e: 来自 time_projection 的调制参数 [B, 6, dim]
    e = (self.modulation + e).chunk(6, dim=1)
    
    # Self-Attention 调制: shift + scale + gate
    y = self.self_attn(
        self.norm1(x).float() * (1 + e[1]) + e[0],  # e[0]=shift, e[1]=scale
        seq_lens, grid_sizes, freqs
    )
    x = x + y * e[2]  # e[2]=gate (初始化为0!)
    
    # Cross-Attention
    x = x + self.cross_attn(self.norm3(x), context, context_lens)
    
    # FFN 调制: shift + scale + gate
    y = self.ffn(self.norm2(x).float() * (1 + e[4]) + e[3])
    x = x + y * e[5]  # e[5]=gate
```

**关键洞察：**
- `self.modulation` 初始化为 `torch.randn(1, 6, dim) / dim**0.5` — 小随机值
- gate 参数 `e[2]` 和 `e[5]` 在训练初期接近 0，意味着注意力输出和 FFN 输出初始被**门控为 0**
- 这保证了训练初期模型行为接近恒等映射，梯度稳定

### 2.5 WanLayerNorm 与 WanRMSNorm

```python
# model.py line 73-102
class WanRMSNorm(nn.Module):
    """RMSNorm: 只用均方根归化，不移除均值"""
    def _norm(self, x):
        return x * torch.rsqrt(x.pow(2).mean(dim=-1, keepdim=True) + self.eps)

class WanLayerNorm(nn.LayerNorm):
    """标准 LayerNorm，但始终用 float32 计算"""
    def forward(self, x):
        return super().forward(x.float()).type_as(x)
```

- **Self-Attention 的 Q/K 用 RMSNorm**（更高效）
- **输入/FFN 前用 LayerNorm**（更稳定）
- 所有归一化**强制 float32 计算**，防止 bf16 精度丢失

### 2.6 Head — 输出层

```python
# model.py line 320-347
class Head(nn.Module):
    def __init__(self, dim, out_dim, patch_size, eps=1e-6):
        out_dim = math.prod(patch_size) * out_dim  # 1*2*2 * 16 = 64
        self.head = nn.Linear(dim, out_dim)
        self.modulation = nn.Parameter(torch.randn(1, 2, dim) / dim**0.5)
    
    def forward(self, x, e):
        e = (self.modulation + e.unsqueeze(1)).chunk(2, dim=1)
        x = self.head(self.norm(x) * (1 + e[1]) + e[0])
        return x
```

**输出还原：**
```
Head 输出: [L, 64]  (64 = 1*2*2 * 16)
         ↓ unpatchify
重建:     [16, F, H, W]  (VAE 潜变量空间)
```

### 2.7 自注意力的 Flash Attention 实现

```python
# attention.py line 24-130
def flash_attention(q, k, v, q_lens=None, k_lens=None, ...):
    """
    优先使用 Flash Attention 3 → Flash Attention 2 → PyTorch SDPA
    支持变长序列 (varlen)，对多分辨率/多帧数视频 batch 至关重要
    """
    if FLASH_ATTN_3_AVAILABLE:
        x = flash_attn_interface.flash_attn_varlen_func(q, k, v, cu_seqlens_q, cu_seqlens_k, ...)
    elif FLASH_ATTN_2_AVAILABLE:
        x = flash_attn.flash_attn_varlen_func(q, k, v, cu_seqlens_q, cu_seqlens_k, ...)
```

**变长序列支持：** 不同视频有不同的帧数 (F) 和分辨率 (H,W)，序列长度 `F * H/2 * W/2` 差异巨大。Flash Attention varlen 模式允许将不同长度的序列**打包成一个 batch**，避免 padding 浪费。


## 三、T5 文本编码器详解 — 为什么用 T5-XXL 而非 CLIP

### 3.1 T5-XXL 编码器配置

```python
# configs/wan_t2v_14B.py
t2v_14B.t5_checkpoint = 'models_t5_umt5-xxl-enc-bf16.pth'
t2v_14B.t5_tokenizer = 'google/umt5-xxl'
# text_dim = 4096 (T5-XXL 的 hidden size)
# text_len = 512 (最大 token 数)
```

### 3.2 T5 在 Wan2.1 中的角色

```python
# model.py line 458-460
self.text_embedding = nn.Sequential(
    nn.Linear(text_dim, dim),    # 4096 → 5120 (14B) 或 1536 (1.3B)
    nn.GELU(approximate='tanh'),
    nn.Linear(dim, dim)
)
```

T5 输出的 4096 维嵌入通过一个 **2 层 MLP 投影**到 DiT 的 hidden_dim，然后作为 Cross-Attention 的 Key/Value：

```python
# Cross-Attention (model.py line 162-184)
def forward(self, x, context, context_lens):
    q = self.norm_q(self.q(x))     # 视频 tokens 作为 Query
    k = self.norm_k(self.k(context))  # T5 文本作为 Key
    v = self.v(context)               # T5 文本作为 Value
    x = flash_attention(q, k, v, k_lens=context_lens)
```

### 3.3 为什么用 T5-XXL 而非 CLIP？

| 维度 | T5-XXL | CLIP ViT-L |
|------|--------|------------|
| **参数** | 11B | 0.4B |
| **序列长度** | 512 tokens | 77 tokens |
| **输出维度** | 4096 | 1024 |
| **训练任务** | 翻译/理解 → **强语义理解** | 图文匹配 → **强视觉对齐** |
| **适合场景** | **复杂描述、长文本** | **短标签、简单描述** |

**核心原因：** 视频生成需要理解**复杂的场景描述**（主体、动作、运镜、风格、空间关系），T5-XXL 的 11B 参数和 512 token 容量提供了足够的语义理解深度。CLIP 虽然视觉对齐好，但文本理解能力远不如 T5-XXL。

### 3.4 文本嵌入处理流程

```
原始 prompt: "一只猫在草地上跑"
         ↓ T5 Tokenizer
Tokens:  [cat, running, on, grass, ...]  (512 tokens, 不足则 padding)
         ↓ T5-XXL Encoder
Embeddings: [512, 4096]
         ↓ text_embedding MLP
Projected: [512, 5120]  (与 DiT hidden_dim 对齐)
         ↓ Concat (I2V 模式下前面加 CLIP 图像 tokens)
Final context: [512+257, 5120]
```

---

## 四、Flow Matching 数学原理 — Diffusion 的升级版

### 4.1 从 Diffusion 到 Flow Matching

传统扩散模型：
$$x_t = \sqrt{\bar{\alpha}_t} x_0 + \sqrt{1-\bar{\alpha}_t} \epsilon, \quad \epsilon \sim \mathcal{N}(0, I)$$

Flow Matching 的核心思想：**直接学习从噪声到数据的最优传输路径**，而非沿着固定的加噪-去噪轨迹。

### 4.2 Flow Matching 的数学推导

**线性插值路径：**
$$x_t = (1-t) \cdot x_0 + t \cdot x_1, \quad t \in [0, 1]$$

其中：
- $x_0$ = 干净数据（VAE 潜变量）
- $x_1$ = 纯噪声（高斯分布）
- $t=0$ → 干净数据，$t=1$ → 纯噪声

**速度场（Velocity Field）：**
$$v = \frac{dx_t}{dt} = x_1 - x_0$$

模型学习的目标：**给定 $x_t$ 和 $t$，预测速度场 $v$**

```python
# 训练时的损失函数 (概念代码)
def flow_matching_loss(model, x0, x1, t):
    xt = (1 - t) * x0 + t * x1          # 线性插值
    v_target = x1 - x0                   # 目标速度
    v_pred = model(xt, t, context)       # 模型预测
    return mse_loss(v_pred, v_target)    # MSE 损失
```

### 4.3 Flow Matching vs 传统 Diffusion

| 特性 | 传统 Diffusion | Flow Matching |
|------|---------------|---------------|
| **加噪路径** | 非线性（由 $\alpha_t$ 定义） | 线性（直接插值） |
| **预测目标** | $\epsilon$ (噪声) 或 $x_0$ | $v = x_1 - x_0$ (速度场) |
| **采样** | 需要 Euler-Maruyama（随机） | 常微分方程 ODE（确定性） |
| **训练稳定性** | 方差调度敏感 | 更稳定（线性路径） |
| **采样效率** | 通常需要 50-100 步 | 可用更少步数（配合 solver） |

### 4.4 Wan2.1 的采样器实现

```python
# wan/utils/fm_solvers.py — Flow Matching 求解器
# 支持多种 ODE solver:
# - Euler (一阶，最快但质量一般)
# - Heun (二阶，质量更好)
# - DPM-Solver (自适应步数，高效)
# - UniPC (高阶，适合高质量采样)
```

**采样过程：**
```python
# 概念代码
def sample(model, noise, context, steps=50):
    xt = noise  # 从纯噪声开始 (t=1)
    for t in reversed(range(steps)):
        v = model(xt, t/steps, context)  # 预测速度
        xt = xt - v * (1/steps)          # 逆向积分 (Euler)
    return xt  # 干净的 VAE 潜变量
```

---

## 五、WanVAE 架构详解 — 3D 因果自编码器

### 5.1 VAE 配置

```python
# configs/wan_t2v_14B.py
t2v_14B.vae_stride = (4, 8, 8)  # 时间×4压缩, 空间×8压缩
```

### 5.2 压缩比计算

```
输入视频: [3, F=81, H=480, W=832]
         ↓ Encoder (stride 4,8,8)
潜变量:   [4, F=20, H=60, W=104]
         (4 channels, 20 frames, 60×104 spatial)
```

**总压缩率：** $4 \times 8 \times 8 = 256$ 倍（体积压缩），通道数从 3→4。

### 5.3 CausalConv3d — 因果 3D 卷积

```python
# vae.py line 17-36
class CausalConv3d(nn.Conv3d):
    """因果 3D 卷积：时间维度只看过去，不看未来"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # padding: (pad_w, pad_w, pad_h, pad_h, 2*pad_t, 0)
        # 时间方向只在过去方向 padding，未来方向不 padding
        self._padding = (self.padding[2], self.padding[2],
                         self.padding[1], self.padding[1],
                         2 * self.padding[0], 0)
    
    def forward(self, x, cache_x=None):
        if cache_x is not None and self._padding[4] > 0:
            # 流式推理：拼接上一批的最后几帧
            x = torch.cat([cache_x, x], dim=2)
        return F.pad(x, padding)  # 然后调用标准 Conv3d
```

**关键设计：因果性**
- 编码器在处理第 $t$ 帧时，**只依赖第 $0$ 到 $t$ 帧**，不依赖未来帧
- 这使得 VAE 支持**流式编码/解码**，可以处理**任意长度的视频**
- 解码器同样因果，保证在线视频生成时不会"看到未来"

### 5.4 流式缓存机制

```python
# vae.py line 14
CACHE_T = 2  # 缓存最近 2 帧

# vae.py line 101-160 (Resample.forward)
def forward(self, x, feat_cache=None, feat_idx=[0]):
    if self.mode == 'upsample3d':
        if feat_cache is not None:
            cache_x = x[:, :, -CACHE_T:, :, :].clone()
            # 如果缓存不足 2 帧，用零填充
            if cache_x.shape[2] < 2:
                cache_x = torch.cat([zeros, cache_x], dim=2)
            x = self.time_conv(x, feat_cache[idx])
            feat_cache[idx] = cache_x  # 保存供下次使用
```

**流式推理的工作方式：**
```
第 1 批: [帧 0-7]    → 编码 → 保存缓存(帧 6-7)
第 2 批: [帧 8-15]   → 编码(需要帧 6-7 作为上下文) → 保存缓存(帧 14-15)
第 3 批: [帧 16-23]  → 编码(需要帧 14-15 作为上下文) → ...
```

### 5.5 Encoder3d 结构

```python
# vae.py line 265-366
class Encoder3d(nn.Module):
    def __init__(self, dim=128, z_dim=4, dim_mult=[1, 2, 4, 4], ...):
        # dim_mult = [1, 2, 4, 4] → channels: 128, 256, 512, 512
        
        self.conv1 = CausalConv3d(3, 128, 3, padding=1)  # 输入层
        
        # 4 个下采样阶段
        # 每个阶段: ResidualBlock × 2 → AttentionBlock (特定尺度) → Downsample
        # 空间下采样 2×2，时间下采样 2×1（在指定层）
        
        self.middle = ResidualBlock + AttentionBlock + ResidualBlock
        
        self.head = RMSNorm + SiLU + CausalConv3d(512, 4, 3, padding=1)  # 输出
```

### 5.6 Decoder3d 结构

与 Encoder 镜像对称，但使用 **上采样**：

```python
# vae.py line 369-472
class Decoder3d(nn.Module):
    def __init__(self, dim=128, z_dim=4, dim_mult=[1, 2, 4, 4],
                 temperal_upsample=[False, True, True], ...):
        # 空间上采样 2×2 (所有 3 次下采样对应上采样)
        # 时间上采样 2×1 (后 2 次，第一次不上采样)
        # 最终: [4, 20, 60, 104] → [3, 81, 480, 832]
```

---

## 六、模型规格对比 — 1.3B vs 14B vs I2V 14B

### 6.1 参数详细对比

| 参数 | T2V-1.3B | T2V-14B | I2V-14B |
|------|----------|---------|---------|
| **hidden_dim** | 1536 | 5120 | 5120 |
| **FFN_dim** | 8960 | 13824 | 13824 |
| **num_heads** | 12 | 40 | 40 |
| **num_layers** | 30 | 40 | 40 |
| **freq_dim** | 256 | 256 | 256 |
| **text_dim** | 4096 | 4096 | 4096 |
| **in_dim** | 16 | 16 | 16 (T2V) / 36 (I2V) |
| **out_dim** | 16 | 16 | 16 |
| **patch_size** | (1, 2, 2) | (1, 2, 2) | (1, 2, 2) |
| **cross_attn_norm** | True | True | True |
| **qk_norm** | True | True | True |

### 6.2 参数量计算

**T2V-1.3B 估算：**
```
30 layers × [
  Self-Attn: 3 × 1536² (QKV) + 1536² (O) = 4 × 2.36M = 9.4M
  Cross-Attn: 同样 9.4M
  FFN: 2 × 1536 × 8960 = 27.5M
] + embeddings + head
≈ 30 × 46.3M + 额外 ≈ 1.3B
```

**T2V-14B 估算：**
```
40 layers × [
  Self-Attn: 4 × 5120² = 104.9M
  Cross-Attn: 104.9M
  FFN: 2 × 5120 × 13824 = 141.6M
] + embeddings + head
≈ 40 × 351.3M + 额外 ≈ 14B
```

### 6.3 为什么 1.3B 和 14B 差距如此之大？

| 维度 | 1.3B | 14B | 倍数 |
|------|------|-----|------|
| hidden_dim | 1536 | 5120 | 3.33× |
| FFN_dim | 8960 | 13824 | 1.54× |
| layers | 30 | 40 | 1.33× |
| 每层参数 | ~43M | ~351M | **8.16×** |

**核心原因：** Transformer 参数量与 $d^2$ 成正比（线性层的权重矩阵）。hidden_dim 从 1536→5120（3.33×），每层的参数量增长约 3.33² ≈ 11×。


## 七、扩散采样流程 — Flow Matching 采样 + I2V 特殊处理

### 7.1 T2V 完整采样流程

```python
# text2video.py 核心流程（概念化）
def generate(prompt, steps=50, H=480, W=832, frames=81, seed=42):
    # 1. 文本编码
    context = t5_encoder(prompt)  # [512, 4096]
    context = text_embedding(context)  # [512, 5120]
    
    # 2. 初始化噪声 (VAE 潜变量空间)
    latent_h, latent_w = H // 8, W // 8  # VAE 空间压缩
    latent_f = (frames - 1) // 4 + 1  # VAE 时间压缩
    noise = torch.randn(1, 16, latent_f, latent_h, latent_w)
    
    # 3. Flow Matching 采样
    xt = noise
    for t in reversed(range(steps)):
        t_norm = t / steps
        # 将 xt 送入 DiT
        v = model(xt, t_norm, context, seq_len=max_tokens)
        # Euler 步逆向积分
        dt = 1.0 / steps
        xt = xt - v * dt
    
    # 4. VAE 解码
    video = vae.decode(xt)  # [1, 3, frames, H, W]
    return video
```

### 7.2 I2V 特殊处理 — 条件视频拼接

```python
# image2video.py line 125-160 (核心逻辑)
def generate(prompt, image, steps=50, ...):
    # 1. 编码参考图
    image_latent = vae.encode_image(image)  # [16, 1, h, w]
    
    # 2. 编码文本
    text_context = t5_encoder(prompt)
    
    # 3. CLIP 图像特征 (I2V 特有)
    clip_fea = clip_encoder(image)  # [1, 257, 1280]
    clip_fea = img_emb(clip_fea)    # [1, 257, 5120]
    
    # 4. 构建噪声 + 参考图拼接
    # 噪声: [16, F, h, w]
    # 参考图: [16, 1, h, w] (重复第 1 帧)
    # Mask: [4, F, h, w] (标记哪些帧已知)
    x0 = torch.cat([noise, mask, image_latent], dim=0)  # [36, F, h, w]
    
    # 5. 采样 (I2V 模型)
    for t in reversed(range(steps)):
        v = i2v_model(xt, t, text_context, clip_fea=clip_fea, y=condition)
        xt = xt - v * dt
    
    # 6. VAE 解码
    return vae.decode(xt)
```

### 7.3 采样器选择

Wan2.1 提供了多种 Flow Matching 求解器（`wan/utils/fm_solvers.py`）：

| 求解器 | 阶数 | 推荐步数 | 速度 | 质量 |
|--------|------|----------|------|------|
| Euler | 1 | 50-100 | 最快 | 一般 |
| Heun | 2 | 30-50 | 中等 | 好 |
| DPM-Solver | 自适应 | 20-30 | 快 | 好 |
| UniPC | 高阶 | 20-30 | 快 | 最好 |

---

## 八、I2V 条件注入与 Mask 机制 — 双路 Cross-Attention、首帧锁定

### 8.1 双路 Cross-Attention

I2V 模型的 Cross-Attention 比 T2V 多了一条路径：

```python
# model.py line 187-229
class WanI2VCrossAttention(WanSelfAttention):
    def __init__(self, dim, num_heads, ...):
        super().__init__(dim, num_heads, ...)
        self.k_img = nn.Linear(dim, dim)   # 图像 Key 投影
        self.v_img = nn.Linear(dim, dim)   # 图像 Value 投影
        self.norm_k_img = WanRMSNorm(dim, eps)
    
    def forward(self, x, context, context_lens):
        # context = [clip_tokens, text_tokens]
        # 分离图像和文本 tokens
        image_context = context[:, :image_context_length]
        text_context = context[:, image_context_length:]
        
        # 路径 1: 文本 Cross-Attention
        q = self.norm_q(self.q(x))
        k = self.norm_k(self.k(text_context))
        v = self.v(text_context)
        x = flash_attention(q, k, v, k_lens=context_lens)
        
        # 路径 2: 图像 Cross-Attention
        k_img = self.norm_k_img(self.k_img(image_context))
        v_img = self.v_img(image_context)
        img_x = flash_attention(q, k_img, v_img, k_lens=None)
        
        # 融合
        x = x + img_x
        x = self.o(x)
        return x
```

**架构意义：** 文本和图像条件**各自独立**做 Cross-Attention，然后在残差中相加。这比拼接所有 tokens 再做一次 Attention 更高效（token 数从 512+257=769 减少到两次独立计算）。

### 8.2 I2V Mask 构造

```python
# image2video.py — Mask 构造逻辑
# 目标: 告诉模型"首帧是已知的参考图，其余帧需要生成"

# 1. 将参考图编码为 VAE 潜变量: [16, 1, h, w]
# 2. 构建时序 Mask: [4, F, h, w]
#    - 第 1 帧 (t=0): Mask 值 = 1 (已知)
#    - 其余帧 (t>0): Mask 值 = 0 (需要生成)
# 3. 拼接:
#    Input = Concat([Noise(16), Mask(4), ImageLatent(16)], dim=0)
#          = [36, F, h, w]
```

**为什么 Mask 是 4 通道？**
VAE 的时间压缩是 4 倍，Mask 需要 4 个通道来对齐 VAE 的时间维度。具体来说：
- Mask 的 4 个通道分别对应 VAE 时间方向上 4 个子帧的信息
- 这样 DiT 可以精确知道哪些子帧包含参考信息，哪些是纯噪声

### 8.3 首帧锁定

在采样过程中，**参考图对应的帧始终不变**：

```python
# 概念代码
for t in reversed(range(steps)):
    xt = xt - v * dt
    # 锁定首帧：用原始参考图替换
    xt[:, :, 0:1, :, :] = original_image_latent
```

这保证了生成的视频**第一帧完全等于输入图像**，不会因采样噪声而偏离。

---

## 九、分布式训练深度解析 — FSDP + USP 序列并行

### 9.1 FSDP (Fully Sharded Data Parallel)

```python
# wan/distributed/fsdp.py
from torch.distributed.fsdp import FullyShardedDataParallel as FSDP

# FSDP 将模型参数、梯度、优化器状态分片到多个 GPU
# 前向传播时按需要全量加载参数
# 反向传播时计算梯度后立即释放
```

**显存优化效果：**

| 策略 | 参数量 (14B) | 梯度 | 优化器状态 (Adam) | 总计 |
|------|-------------|------|-------------------|------|
| 单卡 | 28 GB (bf16) | 28 GB | 56 GB | **112 GB** |
| FSDP (8卡) | 3.5 GB | 3.5 GB | 7 GB | **14 GB/卡** |

### 9.2 USP (Unified Sequence Parallelism) — Ring Attention

```python
# wan/distributed/xdit_context_parallel.py
def usp_attn_forward(q, k, v, ...):
    """使用 Ring Attention 实现序列并行注意力"""
    # q, k, v 按序列维度分片到多个 GPU
    # 通过 ring all-reduce 交换 KV 分片
    # 每个 GPU 计算局部注意力，然后聚合
    
    world_size = dist.get_world_size()
    rank = dist.get_rank()
    
    # Ring Attention 核心循环
    for step in range(world_size):
        # 发送当前 KV 到下一个 rank
        send_rank = (rank + 1) % world_size
        recv_rank = (rank - 1) % world_size
        # ... all-to-all 通信
        
        # 局部 Q 与当前可用的 KV 计算注意力
        partial_out = flash_attention(q_local, k_remote, v_remote, ...)
        # 累加结果
        output = output + partial_out
```

**Ring Attention 白话解释：**

假设你有 8 张 GPU，序列长度 100 万 tokens。每张 GPU 分到 12.5 万 tokens。
- GPU 0 有 Q[0:12.5万]，但需要 K[0:100万], V[0:100万] 来计算完整的注意力
- **Ring Attention 的做法：** GPU 之间像传环一样传递 KV 分片
- 第 1 轮：GPU 0 算 Q[0:12.5万] @ K[0:12.5万],V[0:12.5万]
- 第 2 轮：GPU 7 的 KV 传给 GPU 0，GPU 0 算 Q[0:12.5万] @ K[12.5万:25万],V[12.5万:25万]
- ...8 轮后，GPU 0 有了完整的注意力输出

**通信与计算重叠：** 在 GPU 0 计算第 1 轮注意力的同时，KV 分片已经在网络上传输到下一个 GPU，通信和计算并行，隐藏通信延迟。

### 9.3 分布式训练配置推断

基于源码中的 FSDP + USP 实现：

| 配置 | 推断值 |
|------|--------|
| GPU 类型 | NVIDIA H100 / A100 |
| FSDP 节点 | 8-32 卡 |
| USP 序列并行 | 2-4 路 |
| Batch Size | 每卡 1-2 个视频 |
| 梯度累积 | 4-8 步 |
| 有效 Batch Size | 64-256 |

---

## 十、完整数据流总结

### 10.1 T2V 端到端数据流

```
用户输入: "一只猫在草地上跑"
         ↓
┌─────────────────────────────────────────┐
│ 1. Prompt 扩展 (Qwen2.5-14B)             │
│    → "日系清新风格，一只可爱的橘猫在      │
│       绿色草坪上欢快奔跑，阳光明媚，      │
│       中景跟拍，镜头稳定..."              │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│ 2. T5-XXL 编码                           │
│    Tokens: [512] → Embeddings: [512,4096]│
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│ 3. 初始化噪声                             │
│    noise: [1, 16, 20, 60, 104]           │
│    (16通道 × 20帧 × 60高 × 104宽)        │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│ 4. Flow Matching 采样循环 (50步)          │
│    每步:                                  │
│    a. noise → Patch Embedding            │
│       → [20×60×104, 5120] 序列           │
│    b. + Time Embedding (AdaLN)           │
│    c. × 40 个 WanAttentionBlock           │
│       - Self-Attention (3D RoPE)         │
│       - Cross-Attention (T5 文本)        │
│       - FFN (GELU)                       │
│    d. Head 输出 → unpatchify             │
│    e. Euler 步更新 xt                    │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│ 5. VAE 解码                              │
│    [1, 16, 20, 60, 104] → [1, 3, 81, 480, 832]│
└─────────────────────────────────────────┘
         ↓
输出: 5秒 480P 视频 (81帧, 480×832, 24fps)
```

### 10.2 I2V 数据流差异

```
用户输入: 图片 + "让猫跑起来"
         ↓
 图片 → VAE Encode → [16, 1, 60, 104] (参考图潜变量)
 图片 → CLIP Encode → [1, 257, 1280] → img_emb → [1, 257, 5120]
         ↓
 噪声 [16, F, 60, 104] + Mask [4, F, 60, 104] + 参考图 [16, 1, 60, 104]
         ↓ 拼接为 [36, F, 60, 104]
         ↓ I2V Patch Embedding (接收 36 通道)
         ↓ I2V DiT (40 layers, 双路 Cross-Attention)
         ↓ VAE 解码
输出: 从输入图片开始的连续视频
```


## 十一、Wan2.1 是如何训练出来的 — 两阶段训练、数据格式、时间线推断

### 11.1 训练阶段推断

虽然训练脚本未开源，但从模型架构和配置文件可以推断出两阶段训练策略：

**阶段一：T2V 预训练**
```
数据: 数亿级 视频-文本对
模型: T2V-1.3B 或 T2V-14B
任务: 标准 Flow Matching (噪声 → 视频)
目标: 学习视频生成的基础能力（运动、纹理、时序一致性）
```

**阶段二：I2V 微调**
```
数据: 图片-视频对（视频首帧 + 完整视频）
模型: T2V-14B 初始化
变化: 
  - Patch Embedding 从 16 通道扩展到 36 通道
  - 新增 MLPProj (CLIP → DiT)
  - Cross-Attention 从单路变为双路
目标: 在保持 T2V 能力的同时，学会以图片为条件生成视频
```

### 11.2 训练数据格式推断

```python
# 训练样本结构（推断）
{
    "video": torch.Tensor,      # [3, F, H, W], F=81/129, 多种分辨率
    "text": str,                # 详细描述 (80-100 字)
    "fps": int,                 # 帧率 (通常 24fps)
}
```

**数据预处理流水线：**
```
原始视频 → 抽帧 (不抽帧！保留所有帧) → 归一化到 [-1, 1]
                                    → VAE 编码 → [4, F_latent, H_latent, W_latent]
                                    → 加入随机高斯噪声 → Flow Matching 训练样本
```

**为什么 Wan2.1 不抽帧？**
传统视频生成模型通常从视频中**均匀抽取 16-24 帧**作为训练样本，但 Wan2.1 使用**因果 VAE**，可以处理**任意长度的连续视频**。不抽帧意味着：
- 保留了完整的时序信息，运动更流畅
- VAE 的因果性保证可以处理任意长度，无需固定帧数
- 训练时可以用 81 帧、129 帧等不同长度的视频

### 11.3 3D 张量处理流水线

```
原始视频: [F, H, W, C=3] (如 [81, 480, 832, 3])
         ↓ transpose
      [3, 81, 480, 832]
         ↓ VAE Encoder (stride 4,8,8)
      [4, 20, 60, 104]
         ↓ 加入 Flow Matching 噪声
      xt = (1-t)*x0 + t*x1
         ↓ Patch Embedding (kernel 1,2,2)
      [20, 60, 104, dim=5120]
         ↓ flatten → [124800, 5120] (序列)
         ↓ DiT 40 layers
      [124800, 5120]
         ↓ Head
      [124800, 64] (64 = 1*2*2 * 16)
         ↓ unpatchify
      [4, 20, 60, 104] (VAE 潜变量)
         ↓ 与 x0 计算 Flow Matching Loss
      Loss = MSE(v_pred, v_target)
```

### 11.4 混合精度训练策略

```python
# 从 model.py 源码推断
with amp.autocast(dtype=torch.float32):
    e = self.time_embedding(...)      # 时间嵌入 → float32
    e0 = self.time_projection(e)      # 时间投影 → float32

# 在 WanAttentionBlock.forward 中
with amp.autocast(dtype=torch.float32):
    e = (self.modulation + e).chunk(6, dim=1)
    # AdaLN 调制参数 → float32（保证条件控制精确性）
    x = x + y * e[2]  # gate 乘法 → float32

# 主体计算 → bfloat16
x = self.self_attn(
    self.norm1(x).float() * (1 + e[1]) + e[0],  # norm 输入 → float32
    ...
)
```

**混合精度策略总结：**
- **主体计算：bfloat16** — 节省显存，加速计算
- **AdaLN 调制层：float32** — 保证条件注入精度（shift/scale/gate 对数值精度敏感）
- **所有 Normalization 的输入：float32** — 防止 bf16 下精度丢失导致归一化不稳定
- **输出层：bfloat16** — 正常输出精度

### 11.5 训练时间线推断

| 阶段 | 数据量 | 模型 | 步数 | 时间（估算） |
|------|--------|------|------|-------------|
| T2V-1.3B 预训练 | 数亿 | 1.3B | ~200K | ~2-3 周 (8×H100) |
| T2V-14B 预训练 | 数亿 | 14B | ~200K | ~2-3 月 (128×H100) |
| I2V-14B 微调 | 数千万 | 14B | ~50K | ~1-2 周 (64×H100) |

---

## 十二、关键技术亮点总结

### 12.1 为什么 Wan2.1 比传统 Diffusion 视频模型更强？

| 技术 | 传统模型 | Wan2.1 | 优势 |
|------|---------|--------|------|
| **基础架构** | U-Net | DiT (Transformer) | 更强的序列建模能力 |
| **去噪方式** | 加噪-去噪 | Flow Matching | 更稳定的训练，更少的采样步数 |
| **位置编码** | 1D/2D RoPE | 3D RoPE | 精确的时空位置感知 |
| **条件注入** | 简单的 concat | AdaLN-Zero + 双路 Cross-Attn | 更精确的多模态条件控制 |
| **VAE** | 2D VAE + 插值 | 3D 因果 VAE | 真正的时序一致性，支持任意长度 |
| **文本编码** | CLIP (0.4B, 77 tokens) | T5-XXL (11B, 512 tokens) | 深度语义理解 |

### 12.2 关键设计决策

1. **3D RoPE 频率分配偏向时间维度**（67% vs 33%）— 视频的时序关系比空间更复杂
2. **因果 VAE** — 不抽帧，保留完整时序，支持流式处理
3. **bfloat16 主体 + float32 AdaLN** — 兼顾效率和精度
4. **Flash Attention varlen** — 支持多分辨率/多帧数的混合 batch
5. **I2V 双路 Cross-Attention** — 图像和文本条件独立处理再融合，更高效

---

## 十三、VACE 视频全能创作 (All-in-One)

### 13.1 VACE 是什么

VACE (Video All-in-one Creation and Editing) 是 Wan2.1 的统一视频创作模型，支持：
- 文生视频
- 图生视频
- 视频编辑（替换、修改、风格迁移）
- 视频补全

### 13.2 VACE 架构原理

```python
# wan/modules/vace_model.py
class VACEModel(WanModel):
    """VACE 模型基于 WanModel，增加多条件输入支持"""
    def __init__(self, vace_layers, vace_in_dim, ...):
        # vace_layers: 指定哪些 layer 接收 VACE 条件
        # vace_in_dim: VACE 条件的输入维度
```

**双流架构：**
```
视频帧: [C_in, F, H, W]
  ↓
VACE 条件: [vace_in_dim, F_cond, H, W]
  (可以是: mask, reference, style, edit instruction)
  ↓
拼接: [C_in + vace_in_dim, F, H, W]
  ↓
VACE Patch Embedding (接收扩展通道)
  ↓
指定 layers 接收 VACE 条件 (cross-attn 融合)
  ↓
标准 WanModel 输出
```

### 13.3 VACE 的多任务统一性

VACE 的核心思想：**所有视频创作任务都是"在条件约束下生成视频"**。

| 任务 | 条件类型 | 约束区域 |
|------|---------|---------|
| 文生视频 | 仅文本 | 全局 |
| 图生视频 | 文本 + 首帧图片 | 首帧锁定 |
| 视频编辑 | 文本 + 参考视频 + mask | mask 区域 |
| 视频补全 | 首帧 + 尾帧 | 两端锁定 |

---

## 十四、FLF2V 首尾帧生成

### 14.1 什么是 FLF2V

FLF2V (First-Last-Frame-to-Video) 给定**第一帧和最后一帧**，生成中间的过渡视频。

### 14.2 技术实现

```python
# first_last_frame2video.py 核心逻辑
def generate(prompt, first_frame, last_frame, ...):
    # 1. 编码首尾帧
    first_latent = vae.encode_image(first_frame)   # [16, 1, h, w]
    last_latent = vae.encode_image(last_frame)     # [16, 1, h, w]
    
    # 2. CLIP 编码 (双图)
    clip_fea = clip_encoder(first_frame, last_frame)  # [1, 514, 1280]
    clip_fea = img_emb(clip_fea, flf_pos_emb=True)    # 添加位置嵌入
    
    # 3. 构建条件
    # 首帧锁定在 t=0
    # 尾帧锁定在 t=-1
    # 中间帧需要生成
    
    # 4. 采样
    # FLF2V 模型需要在首尾帧约束下，生成合理的过渡
```

### 14.3 位置嵌入

FLF2V 的 MLPProj 增加了**位置嵌入**（`flf_pos_emb=True`）：

```python
# model.py line 350-369
class MLPProj(torch.nn.Module):
    def __init__(self, in_dim, out_dim, flf_pos_emb=False):
        if flf_pos_emb:
            self.emb_pos = nn.Parameter(
                torch.zeros(1, 257*2, 1280))  # 首帧+尾帧的位置嵌入
    
    def forward(self, image_embeds):
        if hasattr(self, 'emb_pos'):
            image_embeds = image_embeds + self.emb_pos  # 告诉模型这是首帧还是尾帧
        return self.proj(image_embeds)
```

**关键意义：** 位置嵌入让模型区分"这是第一帧"和"这是最后一帧"，否则两张图片的 CLIP 特征没有先后顺序信息。

---

## 十五、推理优化与工程落地

### 15.1 显存优化策略

| 技术 | 效果 | 适用场景 |
|------|------|---------|
| **BF16 推理** | 显存减半 | 所有模型 |
| **T5 Offloading** | 节省 ~20GB | CPU 内存充足时 |
| **VAE Offloading** | 节省 ~5GB | 大分辨率视频 |
| **逐层 Offloading** | 节省 ~30GB | 14B 模型消费级 GPU |

### 15.2 T2V-1.3B 消费级 GPU 运行

```
RTX 4090 (24GB):
  - 模型权重 (bf16): ~2.6GB
  - T5 编码器: ~22GB (可 offload 到 CPU → ~2GB)
  - VAE: ~1GB (可 offload)
  - 激活值 + KV cache: ~5-8GB
  - 总计: ~10-15GB → 8.19GB 起 (极致优化)
```

### 15.3 推理时间估算

| 配置 | 分辨率 | 帧数 | 步数 | 时间 |
|------|--------|------|------|------|
| 1.3B / 4090 | 480P | 81 (5s) | 50 | ~4 分钟 |
| 1.3B / 4090 | 720P | 81 (5s) | 50 | ~8 分钟 |
| 14B / H100 | 480P | 81 (5s) | 50 | ~2 分钟 |
| 14B / H100 | 1080P | 129 (8s) | 50 | ~8 分钟 |

### 15.4 生成质量优化技巧

1. **增加采样步数** (50→100) — 质量提升但时间翻倍
2. **使用 Heun/UniPC 求解器** — 同样步数质量更好
3. **Prompt 扩展** — 简短 prompt 先用 Qwen 扩展为详细描述
4. **多 seed 采样** — 生成 3-5 个版本选最好的
5. **CFG Scale** — 条件引导强度，过高会过饱和，过低会偏离 prompt


## 十六、Prompt 扩展机制 — Qwen2.5 幕后模型

### 16.1 为什么需要 Prompt 扩展

用户通常输入简短的 prompt，如"一只猫"。但高质量视频生成需要详细的场景描述。Wan2.1 内置了基于 Qwen 的 Prompt 扩展系统。

### 16.2 支持的模型（源码确认）

```python
# wan/utils/prompt_extend.py line 364-371
class QwenPromptExpander(PromptExpander):
    model_dict = {
        "QwenVL2.5_3B": "Qwen/Qwen2.5-VL-3B-Instruct",
        "QwenVL2.5_7B": "Qwen/Qwen2.5-VL-7B-Instruct",
        "Qwen2.5_3B": "Qwen/Qwen2.5-3B-Instruct",
        "Qwen2.5_7B": "Qwen/Qwen2.5-7B-Instruct",
        "Qwen2.5_14B": "Qwen/Qwen2.5-14B-Instruct",  # 文本扩展
    }

# wan/utils/prompt_extend.py line 213-249
class DashScopePromptExpander(PromptExpander):
    # 云端 API 模式:
    # - 文本扩展: qwen-plus
    # - 图文扩展: qwen-vl-max
```

### 16.3 System Prompt 设计

扩展模型遵循严格的 System Prompt 指令：

```
核心要求:
1. 补充细节：主体特征、画面风格、空间关系、镜头景别
2. 强调运动信息：运镜方式（推镜头、左移）、自然动作
3. 长度控制：80-100 字左右
4. 默认风格：纪实摄影（除非用户指定）
5. 古诗词处理：强调中国古典元素
```

**扩展示例：**
```
输入: "一只猫"
输出: "日系小清新风格，一只可爱的橘猫在绿色草坪上欢快奔跑，
       阳光明媚，微风拂过，中景跟拍，镜头稳定跟随，
       背景是模糊的公园景色，复古胶片质感照片。"
```

---



## 十七、Wan2.1 的 DiT 与 ViT 架构全面对比

### 17.1 起源关系：DiT 是 ViT 的"超进化版"

**关系链：**
```
NLP Transformer (2017)
    → ViT (2020): Transformer 用于图像分类
    → DiT (2022): Transformer 用于扩散生成
    → Wan2.1 DiT (2025): 3D DiT + Flow Matching + 视频生成
```

| 特性 | ViT (Vision Transformer) | DiT (Diffusion Transformer) | Wan2.1 DiT |
|------|-------------------------|---------------------------|------------|
| **提出时间** | 2020 (Dosovitskiy et al.) | 2022 (Peebles & Xie) | 2025 (阿里通义) |
| **核心任务** | 图像分类（判别式） | 图像生成（扩散模型） | 视频生成（Flow Matching） |
| **输入维度** | 2D [C, H, W] | 2D [C, H, W] | 3D [C, F, H, W] |
| **输出** | 单个类别标签 | 去噪后的图像 | 去噪后的视频潜变量 |
| **位置编码** | 可学习 PE | 可学习 PE / 插值 | 3D RoPE |
| **条件注入** | 无 | AdaLN (时间条件) | AdaLN-Zero + Cross-Attention |

### 17.2 Patch Embedding 对比

**ViT: 2D 卷积，大幅压缩**
```python
# ViT: 将 2D 图像切分为 16×16 的 patch
self.patch_embed = nn.Conv2d(3, dim, kernel_size=16, stride=16)
# 输入: [3, 224, 224] → 输出: [dim, 14, 14] → 序列: [196, dim]
# 压缩比: 256 倍 (16×16)
```

**Wan2.1 DiT: 3D 卷积，轻微压缩**
```python
# Wan2.1: 将 3D 视频切分为 1×2×2 的 patch（时间不压缩！）
self.patch_embed = nn.Conv3d(16, dim, kernel_size=(1,2,2), stride=(1,2,2))
# 输入: [16, 81, 60, 104] → 输出: [dim, 81, 30, 52] → 序列: [198,360, dim]
# 空间压缩比: 4 倍 (2×2)，时间压缩比: 1 倍（不压缩）
```

**关键差异：**
- ViT 的 patch_size=16 是为了**大幅减少 token 数量**（224×224→196 tokens），因为分类任务不需要像素级输出
- Wan2.1 的 patch_size=(1,2,2) 只做**轻微空间压缩**，必须保留 81 帧的完整时间信息
- Wan2.1 的序列长度是 ViT 的 **1000 倍**！这就是为什么需要 Flash Attention

### 17.3 位置编码对比

**ViT: 可学习位置嵌入**
```python
# ViT: 训练时学习的位置嵌入
self.pos_embed = nn.Parameter(torch.zeros(1, 197, dim))
# 197 = 1 (CLS token) + 196 (image patches)
# 问题: 训练时是 196 patches, 推理时如果图像变大（如 336×336 → 441 patches）就不够了!
# 解决: 插值位置嵌入（但效果有损）
```

**Wan2.1 DiT: 3D RoPE（旋转位置编码）**
```python
d = dim // num_heads
self.freqs = torch.cat([
    rope_params(1024, d - 4*(d//6)),  # 时间频率 (67%)
    rope_params(1024, 2*(d//6)),       # 高度频率 (17%)
    rope_params(1024, 2*(d//6)),       # 宽度频率 (17%)
], dim=1)
```

**RoPE vs 可学习 PE 的核心差异：**

| 特性 | ViT 可学习 PE | Wan2.1 3D RoPE |
|------|--------------|----------------|
| 变长支持 | ❌ 需要插值，性能下降 | ✅ 天然支持任意长度 |
| 变分辨率支持 | ❌ 需要 2D 插值 | ✅ 天然支持任意分辨率 |
| 相对位置编码 | ❌ 不显式编码 | ✅ 旋转角差值 = 相对位置 |
| 外推性 | ❌ 超出训练长度性能骤降 | ✅ RoPE 的外推性经过验证 |
| 参数共享 | 每个位置独立参数 | 所有位置共享频率公式 |

**白话类比：**
- **ViT 的 PE** 就像给教室每个座位钉了一个固定编号牌（第1排第1座、第1排第2座...）。如果教室扩建了，新座位没有编号牌，只能临时手写贴上去（插值），效果不好。
- **Wan2.1 的 RoPE** 就像用 GPS 坐标——不管在哪里，按公式算出经纬度。教室扩建了？新座位照样算出精确坐标。

### 17.4 条件注入对比 — DiT 的独门绝技

**ViT: 无条件输入**
```python
# ViT 的输入就是 图像 patch + 位置编码
x = patch_embed(image) + pos_embed
for block in transformer_blocks:
    x = block(x)  # 纯自注意力，没有外部条件
return cls_head(x[:, 0])  # 只用 CLS token 做分类
```

**Wan2.1 DiT: 三重条件注入**
```python
# 条件 1: 时间条件 — AdaLN-Zero
e = time_embed(t)  # 采样步 t → [dim]
e = time_proj(e)   # → [6, dim] = [shift1, scale1, gate1, shift2, scale2, gate2]

# 在每个 Block 中:
y = self_attn(norm1(x) * (1 + e[1]) + e[0])  # shift + scale 调制
x = x + y * e[2]  # gate 控制（初始为0，训练中逐渐学会）

# 条件 2: 文本条件 — Cross-Attention
x = x + cross_attn(norm3(x), text_context)  # T5 文本作为 K/V

# 条件 3: 图像条件 — I2V 额外的 Cross-Attention
x = x + img_cross_attn(norm3(x), clip_context)  # CLIP 图像作为 K/V
```

**为什么 ViT 不需要条件注入？**
- ViT 做分类：输入图像，输出"猫/狗/车"——不需要额外条件
- DiT 做生成：输入噪声 + 文本描述，输出视频——必须知道"生成什么"和"生成到第几步"

**AdaLN-Zero vs LayerNorm：**
| 维度 | ViT LayerNorm | Wan2.1 AdaLN-Zero |
|------|--------------|-------------------|
| 参数来源 | 训练中学习的固定参数 | 由时间 t 动态计算 |
| 公式 | (x - μ) / σ × γ + β | (x - μ) / σ × (1 + scale) + shift |
| Gate 机制 | ❌ 无 | ✅ gate 控制残差输出（初始=0） |
| 初始行为 | 标准归一化 | 接近恒等映射（训练稳定） |

### 17.5 训练目标对比

| 维度 | ViT | Wan2.1 DiT |
|------|-----|------------|
| **任务类型** | 分类（判别式） | 生成（Flow Matching） |
| **损失函数** | 交叉熵 (Cross-Entropy) | MSE(v_pred, x1 - x0) |
| **标签/目标** | 离散类别 (ImageNet 1000 类) | 连续速度场 (从噪声到数据的方向) |
| **监督信号** | "这是猫" | "从噪声到猫的方向是 v" |
| **推理方式** | 单次前向传播 | 50-100 步 ODE 采样循环 |
| **训练批次** | 图像 + 标签 | 视频 → VAE → 潜变量 → 加噪声 → 目标速度 |

**训练流程对比：**
```
ViT 训练:
[图像] → Patch+PE → Transformer → CLS Head → 预测类别
                                       ↓
                                  交叉熵 vs 真实标签
                                       ↓
                                  反向传播

Wan2.1 训练:
[视频] → VAE 编码 → 潜变量 x0 → 线性插值 xt=(1-t)x0+tx1
                                     ↓
                        Patch+RoPE+AdaLN+CrossAttn → 预测速度 v
                                               ↓
                                     MSE vs (x1-x0)
                                               ↓
                                          反向传播
```

### 17.6 计算复杂度对比 — 千倍差距

假设 224×224 图像 (ViT) vs 81×60×104 视频潜变量 (Wan2.1)：

| 指标 | ViT-B/16 | Wan2.1-14B | 倍数 |
|------|----------|------------|------|
| Token 数 | 197 | ~198,360 | **1,000×** |
| 注意力矩阵大小 | 197×197 = 38K | 198K×198K = 39万亿 | **10亿×** |
| 模型参数量 | 86M | 14B | **160×** |
| FLOPs (单次前向) | ~17G | ~2.8T | **160×** |
| 完整采样 FLOPs | 17G (单次) | ~140T (50步) | **8,000×** |
| 训练数据量 | 14M 图像 (ImageNet) | 数亿视频 | **20×** |

**为什么 DiT 必须用 Flash Attention？**
- ViT 的注意力矩阵：197×197×2 bytes = **76 KB** — 随便放
- Wan2.1 的注意力矩阵：198K×198K×2 bytes = **78 TB** — **显存根本装不下！**
- Flash Attention 的优化：不存完整矩阵，**分块计算**，显存从 O(N²) 降到 O(N)

### 17.7 归一化方式对比

**ViT 的归一化：**
```python
# Pre-LN Transformer (标准 ViT)
class ViTBlock(nn.Module):
    def forward(self, x):
        x = x + attn(self.norm1(x))    # LayerNorm 在注意力之前
        x = x + ffn(self.norm2(x))     # LayerNorm 在 FFN 之前
```

**Wan2.1 的归一化：**
```python
# AdaLN-Zero Transformer
class WanBlock(nn.Module):
    def forward(self, x, e):
        # Self-Attention 前: LayerNorm + AdaLN shift/scale
        y = self_attn(self.norm1(x) * (1 + e[1]) + e[0])
        x = x + y * e[2]  # Gate 控制（初始为0）
        
        # Cross-Attention 前: 带 elementwise_affine 的 LayerNorm
        x = x + cross_attn(self.norm3(x), context)
        
        # FFN 前: LayerNorm + AdaLN shift/scale
        y = ffn(self.norm2(x) * (1 + e[4]) + e[3])
        x = x + y * e[5]  # Gate 控制
```

**为什么 DiT 的归一化更复杂？**
- ViT 只需要**稳定训练**——LayerNorm 就够了
- DiT 需要**同时稳定训练 + 注入时间条件**——LayerNorm 本身无法接收时间信号，所以加了 AdaLN

### 17.8 为什么视频生成用 DiT 而不是 ViT？

| 原因 | 说明 |
|------|------|
| **ViT 输出是单个向量** | 分类任务只需输出一个 CLS token 做分类；视频生成需要输出 198K 个 token，每个对应一个时空 patch |
| **ViT 没有条件注入机制** | 视频生成需要时间条件 (t) + 文本条件 (prompt)，ViT 的 LayerNorm 无法动态注入条件 |
| **ViT 位置编码不支持变长** | 视频帧数和分辨率变化巨大，ViT 的可学习 PE 无法处理 |
| **ViT 是判别式模型** | 分类是"输入→标签"的单向映射；生成是"噪声→数据"的逆向过程，需要迭代采样 |
| **DiT 为生成而设计** | AdaLN-Zero、输出 Head、unpatchify 都是专门为像素级生成定制的 |

### 17.9 总结：从 ViT 到 Wan2.1 DiT 的进化路线

```
┌─────────────────────────┐          ┌─────────────────────────┐          ┌──────────────────────────────┐
│ ViT (2020)              │          │ DiT (2022)              │          │ Wan2.1 DiT (2025)            │
│                         │          │                         │          │                              │
│ 📷 2D 图像分类           │    →     │ 🎨 2D 图像生成           │    →     │ 🎬 3D 视频生成                │
│ Patch: Conv2d(16×16)    │          │ Patch: Conv2d(8×8)      │          │ Patch: Conv3d(1×2×2)         │
│ PE: 可学习 (固定长度)    │          │ PE: 可学习/插值          │          │ PE: 3D RoPE (无限长度)       │
│ Norm: LayerNorm         │          │ Norm: AdaLN             │          │ Norm: AdaLN-Zero             │
│ 条件: 无                 │          │ 条件: 时间 t             │          │ 条件: 时间+文本+图像          │
│ 输出: [1, num_classes]  │          │ 输出: [C, H, W] 像素     │          │ 输出: [C, F, H, W] 潜变量    │
│ 损失: 交叉熵             │          │ 损失: MSE (噪声预测)     │          │ 损失: Flow Matching (速度场) │
│ 推理: 1 次前向           │          │ 推理: 50-100 步采样     │          │ 推理: 50-100 步 ODE 采样     │
│ Tokens: ~200            │          │ Tokens: ~256            │          │ Tokens: ~200,000             │
└─────────────────────────┘          └─────────────────────────┘          └──────────────────────────────┘
```

**四大关键进化：**
1. **2D → 3D**：从处理图像到处理视频，增加时间维度的完整建模
2. **固定长度 → 无限长度**：从可学习 PE 到 3D RoPE，支持任意分辨率和帧数
3. **无条件 → 多条件**：从纯视觉输入到文本+图像+时间的多模态条件引导
4. **判别 → 生成**：从"识别世界"到"创造世界"，范式级转变

---

## 十八、源码深度补充 — DiT 完整类定义、RoPE 频率分配、AdaLN 精度控制

### 17.1 WanModel 完整类定义剖析

```python
# wan/modules/model.py line 372-491
class WanModel(ModelMixin, ConfigMixin):
    """Wan diffusion backbone supporting both text-to-video and image-to-video."""
    
    # Diffusers 兼容配置
    ignore_for_config = ['patch_size', 'cross_attn_norm', 'qk_norm', 'text_dim', 'window_size']
    _no_split_modules = ['WanAttentionBlock']  # FSDP 分片提示
    
    @register_to_config
    def __init__(
        self,
        model_type='t2v',          # 't2v' / 'i2v' / 'flf2v' / 'vace'
        patch_size=(1, 2, 2),      # 3D patch 尺寸
        text_len=512,              # T5 最大 token 数
        in_dim=16,                 # VAE 潜变量通道数
        dim=2048,                  # hidden dimension
        ffn_dim=8192,              # FFN 中间维度
        freq_dim=256,              # 时间嵌入维度
        text_dim=4096,             # T5 输出维度
        out_dim=16,                # 输出通道数
        num_heads=16,              # 注意力头数
        num_layers=32,             # Transformer 层数
        window_size=(-1, -1),      # 窗口注意力 (-1=全局)
        qk_norm=True,              # QK 归一化
        cross_attn_norm=True,      # Cross-Attn 归一化
        eps=1e-6,                  # 归一化 epsilon
    ):
```

**完整初始化流程：**

```python
# 1. Patch Embedding: 3D 卷积将视频转为 token 序列
self.patch_embedding = nn.Conv3d(in_dim, dim, kernel_size=patch_size, stride=patch_size)

# 2. Text Embedding 投影: T5 4096 → DiT dim
self.text_embedding = nn.Sequential(
    nn.Linear(text_dim, dim),
    nn.GELU(approximate='tanh'),
    nn.Linear(dim, dim)
)

# 3. Time Embedding: 正弦位置编码 → 投影 → AdaLN 参数
self.time_embedding = nn.Sequential(
    nn.Linear(freq_dim, dim), nn.SiLU(), nn.Linear(dim, dim))
self.time_projection = nn.Sequential(nn.SiLU(), nn.Linear(dim, dim * 6))
# 输出 dim*6 = 6 个调制参数 × dim
# 分配给每个 Block: [shift1, scale1, gate1, shift2, scale2, gate2]

# 4. Transformer Blocks
cross_attn_type = 't2v_cross_attn' if model_type == 't2v' else 'i2v_cross_attn'
self.blocks = nn.ModuleList([
    WanAttentionBlock(cross_attn_type, dim, ffn_dim, num_heads,
                      window_size, qk_norm, cross_attn_norm, eps)
    for _ in range(num_layers)
])

# 5. Head: 最后输出层（也带 AdaLN）
self.head = Head(dim, out_dim, patch_size, eps)

# 6. RoPE 频率预计算
d = dim // num_heads  # head_dim
self.freqs = torch.cat([
    rope_params(1024, d - 4*(d//6)),  # 时间频率 (约 67%)
    rope_params(1024, 2*(d//6)),       # 高度频率 (约 17%)
    rope_params(1024, 2*(d//6)),       # 宽度频率 (约 17%)
], dim=1)

# 7. I2V/FLF2V 特有: CLIP 图像投影
if model_type == 'i2v' or model_type == 'flf2v':
    self.img_emb = MLPProj(1280, dim, flf_pos_emb=model_type == 'flf2v')
```

### 17.2 RoPE 频率分配的精确计算

以 14B 模型为例（dim=5120, num_heads=40, head_dim=128）：

```python
d = 5120 // 40 = 128  # head_dim

# 频率分配:
# 时间: d - 4*(d//6) = 128 - 4*21 = 128 - 84 = 44 维
# 高度: 2*(d//6) = 2*21 = 42 维
# 宽度: 2*(d//6) = 2*21 = 42 维
# 总计: 44 + 42 + 42 = 128 维 ✓

# 频率计算 (theta=10000):
freqs_time = torch.outer(
    torch.arange(1024),  # 位置索引 (最大 1024 个时间步)
    1.0 / torch.pow(10000, torch.arange(0, 44, 2).to(torch.float64).div(44))
)
# shape: [1024, 22] (复数: 实部+虚部)

# 复数极坐标形式:
freqs = torch.polar(torch.ones_like(freqs), freqs)  # e^(i·θ)
```

**频率分布的意义：**

| 维度 | 频率数 | 角度范围 | 物理含义 |
|------|--------|---------|---------|
| 时间 | 22 | 0 ~ 2π/10000 | 慢频率编码长期运动趋势 |
| 高度 | 21 | 0 ~ 2π/10000 | 垂直空间位置 |
| 宽度 | 21 | 0 ~ 2π/10000 | 水平空间位置 |

**RoPE 旋转操作：**

```python
# rope_apply 的核心操作: 复数乘法 = 旋转
x_complex = torch.view_as_complex(x.reshape(..., 2))  # 实数 → 复数
x_rotated = x_complex * freqs  # 复数乘法 (旋转)
x_real = torch.view_as_real(x_rotated).flatten(...)  # 复数 → 实数

# 数学上: [q·cos(θ) - k·sin(θ), q·sin(θ) + k·cos(θ)]
# 这等价于将向量在复平面上旋转 θ 角度
```

### 17.3 AdaLN 调制层的精度控制

```python
# model.py 关键代码 — 为什么 AdaLN 要 float32?
def forward(self, x, e, seq_lens, grid_sizes, freqs, context, context_lens):
    # e 来自 time_projection, 是控制信号
    assert e.dtype == torch.float32  # 强制 float32
    
    with amp.autocast(dtype=torch.float32):
        e = (self.modulation + e).chunk(6, dim=1)
        # modulation 初始值: torch.randn(1, 6, dim) / dim**0.5
        # 例如 dim=5120: std ≈ 1/71.7 ≈ 0.014
    
    # self-attention 的输入调制
    y = self.self_attn(
        self.norm1(x).float() * (1 + e[1]) + e[0],  # shift + scale
        seq_lens, grid_sizes, freqs
    )
    
    with amp.autocast(dtype=torch.float32):
        x = x + y * e[2]  # gate (初始接近 0)
    
    # ... cross-attention 和 FFN 同样处理
    
    # 为什么 float32?
    # 1. e[2] 和 e[5] (gate) 初始值 ≈ 0, bf16 精度不够可能下溢
    # 2. (1 + e[1]) 中 e[1] 很小, bf16 下 1 + 0.014 = 1.0 (精度丢失!)
    # 3. AdaLN 控制整个模型的时序行为, 需要高精度
```

**bf16 vs float32 精度对比：**
```
bf16:  8 bit mantissa → 精度约 2 位小数 → 1.0 + 0.014 = 1.0 (丢失!)
float32: 23 bit mantissa → 精度约 7 位小数 → 1.0 + 0.014 = 1.014 (精确!)
```

---

## 十九、I2V 输入张量结构：36 通道之谜

### 18.1 具体的通道拼接过程

在 I2V（图生视频）任务中，DiT 模型接收的输入并不是简单的 16 通道噪声，而是由三部分拼接而成的 **36 通道张量**。

**三个组成部分：**

1. **噪声 (Noise)**：
   - 形状：`[16, F, h, w]`
   - 这是生成的起点，随机高斯噪声

2. **参考图潜变量 (Image Latent)**：
   - 形状：`[16, 1, h, w]`（注意：只有一帧）
   - 通过 VAE 编码参考图得到

3. **时序掩码 (Temporal Mask)**：
   - 形状：`[4, F, h, w]`
   - 为了对齐 VAE 的 4 倍时间压缩，Mask 被 reshape 为 4 个通道
   - 作用：告诉模型"哪些是已知的参考帧，哪些是需要生成的未知帧"

**拼接公式：**
```
Input_DiT = Concat([Noise_16, Mask_4, ImageLatent_16], dim=0)
          = [36, F, h, w]
```

### 18.2 Patch Embedding 的适配

由于输入变成了 36 通道，I2V 模型的 **Patch Embedding（第一层卷积）** 必须能够接收 36 个通道的输入：

```python
# T2V: Conv3d(16, dim, kernel=(1,2,2), stride=(1,2,2))
# I2V: Conv3d(36, dim, kernel=(1,2,2), stride=(1,2,2))
# 差异: in_channels 从 16 → 36

# I2V 微调时，Patch Embedding 权重的扩展方式:
# 方案 1: 随机初始化新增 20 通道的权重
# 方案 2: 复制噪声通道的权重 + 噪声初始化
# Wan2.1 采用的方式需要查看 checkpoint 差异
```

### 18.3 image2video.py 中的实际拼接代码

```python
# image2video.py 核心逻辑（概念化）
def _get_image_condition(self, image, num_frames):
    """构建 I2V 条件输入"""
    # 1. 编码参考图
    image_latent = self.vae.encode(image)  # [1, 16, 1, h, w]
    image_latent = image_latent.squeeze(2)  # [16, 1, h, w]
    
    # 2. 构建时序 Mask
    mask = torch.zeros(4, num_frames, h, w)  # 4 通道, F 帧
    mask[:, 0, :, :] = 1.0  # 首帧标记为已知
    
    # 3. 拼接
    x = torch.cat([noise, mask, image_latent], dim=0)  # [36, F, h, w]
    
    # 4. 对于条件视频 (y), 同样拼接
    # y 在模型 forward 中与 x 拼接后再处理
    return x
```

---

## 二十、训练数据深度解析 — 数据从哪儿来、为什么不抽帧

### 19.1 训练数据来源推断

基于 Wan2.1 的能力（生成中英文文字、复杂动作、多种风格），训练数据应包含：

| 数据类型 | 推断比例 | 说明 |
|---------|---------|------|
| 影视片段 | ~30% | 高质量电影、动画、广告 |
| 用户生成视频 | ~25% | YouTube、Bilibili 等 |
| 专业拍摄 | ~20% | 高分辨率、高质量运镜 |
| 动画/CG | ~15% | 3D 动画、游戏过场 |
| 文字视频 | ~5% | 含中英文文字的视频 |
| 其他 | ~5% | 艺术视频、实验影像 |

### 19.2 数据清洗流程推断

```
原始数据池 (数亿视频)
         ↓
1. 美学评分模型 (去除模糊、低质量)
         ↓
2. 文本相关性过滤 (CLIP Score, 去除图文不符)
         ↓
3. 时间一致性检测 (去除抖动剧烈、跳帧片段)
         ↓
4. 多分辨率统一 (480p ~ 1080p, 配合 3D RoPE 泛化)
         ↓
5. 文本描述生成/清洗 (80-100 字详细描述)
         ↓
干净训练集
```

### 19.3 3D 因果卷积的流式缓存机制

```python
# vae.py 中 CausalConv3d 的缓存机制
CACHE_T = 2  # 缓存最近 2 帧

def forward(self, x, cache_x=None):
    padding = list(self._padding)
    if cache_x is not None and self._padding[4] > 0:
        cache_x = cache_x.to(x.device)
        x = torch.cat([cache_x, x], dim=2)  # 拼接缓存帧
        padding[4] -= cache_x.shape[2]
    x = F.pad(x, padding)
    return super().forward(x)
```

**流式处理详解：**

```
时间轴: ──────●───────●───────●───────●──→
            帧0     帧15    帧30    帧45

编码流程:
批次1 [帧0-15]:  → 编码 → 缓存最后2帧 (帧14-15)
批次2 [帧16-31]: → 需要帧14-15作为上下文 → 编码 → 缓存帧30-31
批次3 [帧32-47]: → 需要帧30-31作为上下文 → 编码 → ...

为什么需要缓存?
- 3D 卷积核大小=3, 需要前后各1帧的上下文
- 因果性要求: 只看过去,不看未来
- 所以只需缓存过去的帧,不需要预加载未来帧
```

### 19.4 为什么不抽帧？

传统视频生成模型（如 SVD、Video LDM）通常从视频中**均匀抽取 16-24 帧**作为训练样本。Wan2.1 不抽帧的原因：

1. **3D 因果 VAE 支持任意长度**：不需要固定帧数输入
2. **保留完整时序信息**：81 帧 vs 16 帧，运动信息量 5×
3. **流式训练**：可以处理超长视频，按 chunk 分批训练
4. **分辨率泛化**：3D RoPE 天然支持不同长度/分辨率的视频

**代价：**
- 训练数据预处理更复杂（需要 VAE 编码）
- 显存占用更大（81 帧 vs 16 帧的潜变量）
- 需要 FSDP + USP 等分布式训练技术

---

## 二十一、深入问答 — VAE 和不抽帧的关系、2D/3D 卷积区别

### 20.1 VAE 和不抽帧是独立的设计选择

**常见误解：** "因为 VAE 压缩了时间维度（×4），所以可以不抽帧"

**事实：** 这是**两个独立的设计选择**：

```
选择 A: 用什么 VAE?
  → 传统 2D VAE: 逐帧编码, 时间信息丢失
  → 3D 因果 VAE: 时空联合编码, 保留时序 ✓

选择 B: 抽帧还是不抽帧?
  → 抽帧: 从视频中选 16-24 帧 (传统做法)
  → 不抽帧: 保留所有帧 (Wan2.1 做法)
```

**组合效果：**

| VAE 类型 | 抽帧 | 效果 | 典型模型 |
|----------|------|------|---------|
| 2D VAE | 是 | 运动不流畅 | SVD |
| 2D VAE | 否 | 帧间独立, 时间不一致 | 不可行 |
| 3D VAE | 是 | 浪费 VAE 能力 | 少见 |
| 3D VAE | 否 | 完整时序, 运动流畅 ✓ | Wan2.1 |

**结论：** 3D 因果 VAE 是不抽帧的**前提条件**，但不抽帧是一个**额外的设计决策**，目的是最大化利用 3D VAE 的能力。

### 20.2 2D 卷积 vs 3D 卷积的维度概念

**2D 卷积（传统图像）：**
```
输入: [C, H, W] (3通道, 高×宽)
卷积核: [C_out, C_in, kH, kW]
操作: 在 H×W 平面上滑动
输出: [C_out, H', W']
```

**3D 卷积（视频）：**
```
输入: [C, T, H, W] (3通道, 时间×高×宽)
卷积核: [C_out, C_in, kT, kH, kW]
操作: 在 T×H×W 立体空间中滑动
输出: [C_out, T', H', W']
```

**关键区别：**

| 维度 | 2D 卷积 | 3D 卷积 |
|------|---------|---------|
| 滑动维度 | H, W | T, H, W |
| 感受野 | 空间邻域 | 时空邻域 |
| 参数量 | C_out×C_in×kH×kW | C_out×C_in×kT×kH×kW |
| 因果性 | N/A | 可设计为只看过去 |

**Wan2.1 中 3D 卷积的具体参数：**
```python
# CausalConv3d(kernel_size=3, padding=1)
# kernel: (3, 3, 3) → 时间3帧, 空间3×3像素
# padding: (1, 1, 1) → 但时间方向只在过去方向 padding
# 等效 padding: (0, 1, 1) + 过去1帧的缓存
```

### 20.3 多分辨率训练与 3D RoPE 泛化

Wan2.1 使用 3D RoPE 实现对不同分辨率/帧数的泛化：

```python
# RoPE 的关键特性: 相对位置编码
# 不管视频是 480P 还是 1080P, 两个 patch 的相对位置编码方式相同

# 训练时混合分辨率:
batch = [
    (480P, 81帧),   # 低分辨率长视频
    (720P, 81帧),   # 中分辨率
    (1080P, 41帧),  # 高分辨率短视频
    (480P, 129帧),  # 低分辨率超长视频
]

# RoPE 对每种分辨率自动生成对应的位置编码:
for video in batch:
    F, H, W = video.shape[-3:]
    freqs = compute_rope_freqs(F // 4, H // 8, W // 8)  # 按实际尺寸
    # 不同尺寸的视频共享同一套 RoPE 参数
```

**泛化效果：** 训练时见过 480P，推理时可以直接生成 1080P——因为 RoPE 编码的是**相对位置**而非绝对坐标。


## 📚 附录：专业词汇通俗解释

### 1. DiT (Diffusion Transformer)

**一句话：** 用 Transformer 来做扩散生成的模型，取代传统的 U-Net。

**类比：** 传统扩散模型像一个水管工（U-Net），从上到下再从下到上修管道。DiT 则像一个翻译官（Transformer），把噪声"翻译"成视频——逐层理解每一部分该变成什么样。

**为什么比 U-Net 好：** Transformer 的自注意力机制能看到**全局信息**，而 U-Net 的卷积主要看**局部区域**。生成视频这种需要全局一致性的任务，Transformer 更擅长。

### 2. Flow Matching (流匹配)

**一句话：** 让模型学习从噪声到数据的"最优传输路径"。

**类比：** 想象你要把一杯混浊的水（噪声）变成一杯纯净水（数据）。传统扩散模型是随机搅动让杂质慢慢沉淀。Flow Matching 则是画一条从混浊到纯净的**直线管道**，水沿着管道直接流过去。

**在 Wan2.1 中的体现：** 模型不再预测"噪声是什么"，而是预测"下一步往哪个方向走"（速度场）。这使得采样可以用确定的 ODE 求解器，而不是随机采样。

### 3. RoPE (Rotary Position Embedding, 旋转位置编码)

**一句话：** 用复数旋转来告诉模型"每个 token 在什么位置"。

**类比：** 想象你在给排队的人编号。普通位置编码是给人戴不同颜色的帽子（绝对位置）。RoPE 则是让每个人按位置旋转一个角度——两个人之间的距离就是角度的差值。**旋转的好处：** 不管队伍多长，两个人的相对位置关系永远不变。

**3D RoPE 的特殊之处：** Wan2.1 的 RoPE 同时在**时间、高度、宽度**三个维度上旋转。时间维度占 67% 的频率分量，因为视频的"什么时候"比"在哪个像素"更重要。

### 4. AdaLN-Zero (Adaptive Layer Normalization with Zero Initialization)

**一句话：** 让时间条件动态调整每一层的归一化参数，且初始为零。

**类比：** 想象你在调音响。LayerNorm 是基础音量。AdaLN 是你可以根据时间 t 调整音量（scale）、低音（shift）、是否开启（gate）。**Zero Initialization** 意味着初始状态下，这些调整都是 0——音响保持原始状态，不被干扰。训练过程中，模型慢慢学会在什么时间该调多大。

### 5. VAE (Variational Autoencoder, 变分自编码器)

**一句话：** 把视频压缩到一个小空间（潜变量），生成完再解压回来。

**类比：** VAE Encoder 像一个压缩软件，把 1GB 的视频压缩成 4MB 的压缩包（潜变量）。DiT 在这个小空间里生成内容（快、省资源）。VAE Decoder 再把压缩包解压成视频。

**Wan-VAE 的特殊之处：** 它是**因果的**——编码第 t 帧时不需要看未来的帧。这使得它可以处理**任意长度的视频**，不像传统 VAE 需要固定帧数。

### 6. Flash Attention

**一句话：** 一种超快的注意力计算方式，不用把所有 QK 分数存到显存里。

**类比：** 传统 Attention 像一个学生做题：把所有题目的答案都写在草稿纸上（显存占用大），最后再看。Flash Attention 像学生边算边写答案——只记住必要的中间结果（显存占用小），速度还快。

**在 Wan2.1 中：** 支持**变长序列**（varlen），不同长度/分辨率的视频可以打包成一个 batch，不用 padding 浪费计算。

### 7. Cross-Attention (交叉注意力)

**一句话：** 让视频 tokens "查询"文本 tokens，理解文本该指导视频生成。

**类比：** 想象你在画一幅画，旁边有一本说明书（文本）。Cross-Attention 就是你不时地看一眼说明书（Query 视频 tokens → Key/Value 文本 tokens），确保你画的内容符合说明。

**Wan2.1 I2V 的双路 Cross-Attention：** 同时看两本说明书——一本是文本描述（T5），一本是参考图片（CLIP），然后综合理解。

### 8. FSDP (Fully Sharded Data Parallel)

**一句话：** 把模型的参数、梯度、优化器状态分片到多张 GPU 上。

**类比：** 假设一本字典有 14000 页（14B 参数），一张桌子放不下（单卡显存不够）。FSDP 的做法是：8 张桌子各放 1750 页，需要哪页就去对应桌子拿。算完梯度后，大家同步一下。

### 9. Ring Attention

**一句话：** 多张 GPU 像传环一样传递 KV 分片，实现超长序列的注意力计算。

**类比：** 8 个人合作写一篇长文，每人写 1 章。但每个人的章节都需要参考其他章节。Ring Attention 就是：我把我的章节传给你，你把你的传给我，大家轮流看，最终每人都看完了所有章节。关键是**边看边传**，不用等。

### 10. Causal Conv3d (因果 3D 卷积)

**一句话：** 卷积核在时间维度上只"看过去"，不"看未来"。

**类比：** 你看电影时，因果卷积意味着你只能根据已经播放的画面做判断，不能偷看后面的剧情。这使得视频编码可以**逐段处理**（流式），不需要等整个视频加载完。

### 11. Patch Embedding

**一句话：** 把视频切成小块（patch），用卷积把每块变成一个向量（token）。

**类比：** 拼图。一张大图片切成很多小方块（patch），每个方块用一个数字表示（embedding）。DiT 处理的不是像素，而是这些方块对应的数字。

**Wan2.1 的 patch_size=(1,2,2)：** 时间方向 1 帧一切，空间方向 2×2 像素一切。所以一帧 480×832 的图像变成 240×416 个 patch。

### 12. bfloat16 (Brain Float 16)

**一句话：** 一种 16 位浮点数格式，和 32 位浮点有相同的指数范围。

**类比：** float32 像一个精确到毫米的尺子（16 位精度，16 位范围）。float16 像精确到厘米但只能量 1 米的尺子（10 位精度，5 位范围）。bfloat16 像精确到厘米但能**量到 1 公里**的尺子（8 位精度，16 位范围）——精度低一些，但不会溢出。

**为什么 Wan2.1 用 bfloat16：** 生成视频时容易出现很大的激活值（NaN 溢出），bfloat16 的大范围能防止这个问题。

### 13. GELU (Gaussian Error Linear Unit)

**一句话：** 一种激活函数，比 ReLU 更平滑。

**类比：** ReLU 像一个只有"开/关"的开关——正的通过，负的截断。GELU 像一个**智能阀门**——根据输入大小自动调节通过量，小的输入少通过一点，大的输入全通过。

**Wan2.1 用 GELU(approximate='tanh')：** tanh 近似版本计算更快，精度损失可忽略。

### 14. CFG Scale (Classifier-Free Guidance)

**一句话：** 控制生成结果对 prompt 的"忠实度"。

**类比：** 你请画家画一幅画，CFG 高意味着"严格按你的描述画"，CFG 低意味着"画家有更多自由发挥"。太高会过度饱和，太低会偏离你的描述。

### 15. 潜变量空间 (Latent Space)

**一句话：** 压缩后的数据表示，维度远低于原始数据。

**类比：** 原始视频是一张巨大的画布（3×81×480×832 ≈ 100M 像素）。潜变量空间是一张**缩略图**（4×20×60×104 ≈ 50K 像素）。DiT 在缩略图上工作，效率提升 2000 倍。VAE 负责把缩略图还原成完整画布。

---

## 附录 B：核心源码文件索引

| 文件 | 行数 | 主要类/函数 |
|------|------|------------|
| `wan/modules/model.py` | 631 | `WanModel`, `WanAttentionBlock`, `Head` |
| `wan/modules/attention.py` | 179 | `flash_attention`, `attention` |
| `wan/modules/vae.py` | 663 | `WanVAE`, `CausalConv3d`, `Encoder3d`, `Decoder3d` |
| `wan/modules/t5.py` | 513 | T5 编码器实现 |
| `wan/modules/clip.py` | 542 | CLIP 图像编码器 |
| `wan/configs/wan_t2v_14B.py` | 29 | 14B T2V 配置 |
| `wan/configs/wan_t2v_1_3B.py` | 29 | 1.3B T2V 配置 |
| `wan/configs/wan_i2v_14B.py` | 36 | 14B I2V 配置 |
| `wan/image2video.py` | 350 | I2V 推理管线 |
| `wan/text2video.py` | 271 | T2V 推理管线 |
| `wan/first_last_frame2video.py` | 377 | FLF2V 推理管线 |
| `wan/distributed/fsdp.py` | 43 | FSDP 配置 |
| `wan/distributed/xdit_context_parallel.py` | 226 | Ring Attention 实现 |
| `wan/utils/prompt_extend.py` | 647 | Prompt 扩展系统 |
| `wan/vace.py` | 797 | VACE 全能创作 |
| `wan/modules/vace_model.py` | 250 | VACE 模型定义 |
| `wan/utils/fm_solvers.py` | - | Flow Matching 求解器 |
| `generate.py` | 587 | 统一生成入口 |

---

*文档基于 Wan-Video/Wan2.1 开源项目源码分析生成*
*GitHub: https://github.com/Wan-Video/Wan2.1*
*技术报告: https://github.com/Wan-Video/Wan2.1/blob/main/assets/technical_report.pdf*
