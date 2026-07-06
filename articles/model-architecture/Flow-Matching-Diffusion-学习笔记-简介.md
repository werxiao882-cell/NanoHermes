# Flow Matching 和 Diffusion Models 学习笔记（一）：简介

> **原文链接**：https://mp.weixin.qq.com/s/CNNWx73QTZ7yYUemt62URA
> **系列**：MIT 6.S184 "Generative AI with Stochastic Differential Equations" 课程笔记
> **期数**：第一期 · §1 Introduction

---

> 本系列笔记基于 MIT 6.S184 *"Generative AI with Stochastic Differential Equations"* 课程讲义。 第一期对应讲义 §1 Introduction（p.3 – p.6），挑选最核心的几个点做精读与延伸。

> *Creating noise from data is easy; creating data from noise is generative modeling.* —— Song et al.

这句话几乎是整门课的"题眼"。把一张清晰的图片糊成噪声（加噪）是轻而易举的；但反过来，从一团纯随机噪声里"雕"出一只栩栩如生的小狗，才是 **生成式建模（generative modeling）** 真正要解决的问题。所谓 **扩散模型（diffusion models）** 与 **流匹配（flow matching）** ，本质上就是在学习这条"噪声 → 数据"的反向通路。

过去十余年，大多数 AI 系统在做的都是 **预测（prediction）** ：给定输入 ![formula_00](images/flow-matching-diffusion/formula_00.svg) ，输出一个标签 ![formula_01](images/flow-matching-diffusion/formula_01.svg) 。图像分类、语音识别、欺诈检测，莫不如此。

而现在我们见到的 Nano Banana、Stable Diffusion 3、VEO‑3、ChatGPT，它们在干一件根本不同的事—— **生成（generation）** ：凭空（或者按照一句提示）"造"出一张原本不存在的图、一段视频、一段话。

课程作者强调： **这是近年 AI 革命真正的能力跃迁** 。从"判别"到"创造"，意味着 AI 系统第一次具备了"想象力"。本课程要讲的两类算法—— **去噪扩散模型（Denoising Diffusion Models）** 与 **流匹配（Flow Matching）** ——正是这场革命的发动机：

- 图像 / 视频 ：Stable Diffusion、FLUX、Nano Banana、VEO‑3
- 科学应用 ：AlphaFold 3（蛋白质结构预测）也是一个扩散模型

> **拓展** ： **判别模型（discriminative model）** 建模的是 ![formula_02](images/flow-matching-diffusion/formula_02.svg) （"已知图是什么，给一个标签"），而 **生成模型（generative model）** 建模的是 ![formula_03](images/flow-matching-diffusion/formula_03.svg) 或 ![formula_04](images/flow-matching-diffusion/formula_04.svg) （"已知描述，画一张图"）。前者是选择题，后者是开放题，难度天差地别。

讲义里有一句话值得画重点：

> *All of these generative models generate objects by iteratively converting noise into data.*

所有这些生成模型，都是通过 **迭代地把噪声变成数据（iteratively converting noise into data）** 来完成生成的。而这个"迭代变换"的数学载体是：

![formula_05](images/flow-matching-diffusion/formula_05.svg)

整门课的任务可以浓缩成一句话：

> **用深度神经网络大规模地构造、训练、模拟 ODE / SDE，把随机噪声"流"成目标数据。**

这也解释了为什么讲义会先补一块"微分方程"的数学准备——不把 ODE/SDE 这套工具讲清楚，后面的流匹配、 **分数匹配（score matching）** 都会像空中楼阁。

| 章节 | 主题 | 学什么 |
|------|------|--------|
| §1 | Generative Modeling as Sampling | 把"生成"严格化为"从分布采样" |
| §2 | Flow & Diffusion Models | 生成的"机械原理"：ODE / SDE |
| §3 | Flow Matching | 现代大模型的核心训练算法 |
| §4 | Score Matching（分数匹配） | 扩散模型的训练算法，解锁 SDE 采样与引导 |
| §5 | Guidance（引导） | 如何让模型"听话"（classifier‑free guidance，无分类器引导） |
| §6 | Latent Spaces（潜空间） & NN 架构 | 怎么真正搭出 Nano Banana 这种大模型 |
| §7（选修） | Discrete Diffusion（离散扩散） | 把扩散思想迁移到文本等离散数据 |

可以看出： **§3 和 §4 是核心战役** ，前两章打地基，后三章讲工程化与扩展。

这是 §1.3 的核心，也是本期最需要咀嚼的部分。作者用四个 Key Idea，把"生成一张图"一步步变成一个干净的数学问题。

无论是图像、视频还是分子结构，都可以被"拍扁"成一个实数向量：

- 图像 ： （高 × 宽 × RGB 三通道）
- 视频 ： （再加一个时间维度）
- 分子 ： （ 个原子的 3D 坐标）

统一写作：

![formula_06](images/flow-matching-diffusion/formula_06.svg)

> **注意** ：文本是一个显著的例外——它天然离散，由语言模型处理，属于 §7 的范畴。本课程的主战场是 **连续向量空间（continuous vector space）** 。

怎么定义"生成一张狗的图"？不是生成 **那一张** 狗——世界上没有唯一最优的狗图。更合理的视角是：

> 所有"长得像狗"的图像，在"图像空间（space of images）"中构成了一个区域；这个区域上存在一个 **概率密度（probability density）** ![formula_07](images/flow-matching-diffusion/formula_07.svg) ，越像狗的地方密度越高。

于是"生成一张狗图"被翻译成：

![formula_08](images/flow-matching-diffusion/formula_08.svg)

即 **从数据分布（data distribution）中采样（sampling）一个样本** 。这一步翻译极其关键：它把一个主观问题（"像不像狗"）替换成了一个客观问题（"在 ![formula_09](images/flow-matching-diffusion/formula_09.svg) 下的 **似然（likelihood）** 有多大"）。

现实中我们从来看不到真正的 ![formula_10](images/flow-matching-diffusion/formula_10.svg) ，只能拿到它的一批 **独立同分布样本（i.i.d. samples）** ，即所谓的 **数据集（dataset）** ：

![formula_11](images/flow-matching-diffusion/formula_11.svg)

- 图像：从互联网爬取
- 视频：YouTube
- 蛋白质：RCSB Protein Data Bank（几十万个实验测定的结构）

数据集越大，它对真实分布的"代理"就越准。

> **拓展** ：这正好解释了为什么 "scale matters"——更大的数据集 ≈ 更接近真正的 ![formula_12](images/flow-matching-diffusion/formula_12.svg) ，模型学到的分布也就越贴近现实世界。

我们平时用 AI 画图，输入的都是 prompt，比如 "一只在雪山背景下奔跑的狗"。这对应数学上的 **条件分布（conditional distribution）** ，讲义中称为 **引导数据分布（guided data distribution）** ：

![formula_13](images/flow-matching-diffusion/formula_13.svg)

其中 ![formula_14](images/flow-matching-diffusion/formula_14.svg) 是条件变量（文本、类别、草图……）。作者还特地说了一句很关键的话：

> **无条件生成（unconditional generation）的技术，都能比较直接地推广到条件生成（conditional generation）。**

所以前三章会先专注于无条件情形（ ![formula_15](images/flow-matching-diffusion/formula_15.svg) ），等工具成熟后，再到 §5 统一处理 **引导（guidance）** 问题。这是一种"先把最硬的骨头啃掉"的教学路径。

将 §1.3 末尾的 Summary 2 翻译并浓缩如下：

1. 研究对象 ：可以写成向量 ![formula_16](images/flow-matching-diffusion/formula_16.svg) 的事物——图像、视频、分子结构。
2. 生成的定义 ：从一个概率分布 ![formula_17](images/flow-matching-diffusion/formula_17.svg) 中采样。
3. 训练信号 ：我们只拥有来自 ![formula_18](images/flow-matching-diffusion/formula_18.svg) 的一批样本 ![formula_19](images/flow-matching-diffusion/formula_19.svg) ，而非分布本身。
4. 条件生成 ：把目标换成从 ![formula_20](images/flow-matching-diffusion/formula_20.svg) 采样，训练集变成配对数据 ![formula_21](images/flow-matching-diffusion/formula_21.svg) 。
5. 最终目标 ：构造一个训练后能从 ![formula_22](images/flow-matching-diffusion/formula_22.svg) 采样的"生成机器"。

一句话记住这期：

> **生成 = 从一个你看不见、只有样本的分布里，学会重新采样。**

而 flow matching 与 diffusion，就是当下把这件事做得最好的那把钥匙。

*下一期我们进入 §2，开始拆解这台"生成机器"背后的 ODE / SDE 数学工具。*

---

## 📚 专业词汇通俗解释

### 1. Flow Matching（流匹配）

**一句话解释**：一种训练生成模型的新方法，通过学习"如何把噪声平滑地变成数据"来生成内容。

**通俗类比**：想象你要教 AI 如何把一团随机散落的沙子（噪声）堆成一座城堡（数据）。Flow Matching 就是教 AI 学习从"沙子"到"城堡"的每一步应该怎么移动。与 Diffusion 不同，它走的是"确定性路线"（ODE），就像有 GPS 导航一样精确。

| 特性 | Diffusion Models | Flow Matching |
|------|-----------------|---------------|
| 数学基础 | 随机微分方程（SDE） | 常微分方程（ODE） |
| 路径 | 随机游走 | 确定性轨迹 |
| 训练 | Score Matching | 直接学习向量场 |
| 采样 | 需要多步去噪 | 解 ODE 积分 |

### 2. Diffusion Models（扩散模型）

**一句话解释**：通过"加噪→去噪"过程学习数据分布的生成模型。

**通俗类比**：就像你先看一张清晰的照片，然后慢慢往上面撒沙子直到完全看不清（前向加噪）。然后你学习如何从一堆沙子中"逆向工程"出原来的照片（反向去噪）。AI 学会了这个逆向过程，就能从纯噪声中"雕"出任何图像。

**关键论文**：DDPM（Denoising Diffusion Probabilistic Models）、Stable Diffusion（Latent Diffusion）

### 3. ODE（常微分方程）

**一句话解释**：描述一个变量如何随时间连续变化的数学方程。

**通俗类比**：就像你知道一辆车的当前位置和速度，ODE 告诉你未来任意时刻车会在哪里。在生成模型中，ODE 描述了从噪声点到数据点的"确定路线"。

**公式**：`dx/dt = v(x, t)`，其中 `v` 是神经网络学习的速度场。

### 4. SDE（随机微分方程）

**一句话解释**：ODE 的"随机版"，加入了随机噪声项。

**通俗类比**：还是那辆车，但现在路上有随机阵风（布朗运动），车的轨迹不再是确定的。Diffusion Models 使用 SDE，因为加噪过程本身是随机的。

**公式**：`dx = f(x,t)dt + g(t)dw`，其中 `dw` 是随机噪声。

### 5. Score Matching（分数匹配）

**一句话解释**：一种训练方法，让模型学习数据分布的"梯度方向"（分数函数）。

**通俗类比**：想象你在山里迷路了，分数函数就是告诉你"往哪个方向走海拔会升高"。在生成模型中，分数告诉你"往哪个方向调整噪声会更像真实数据"。

**数学定义**：`∇ₓ log p(x)`，即数据分布的对数概率梯度。

### 6. Generative Modeling（生成式建模）

**一句话解释**：学习数据的分布，然后从中采样生成新数据。

**通俗类比**：
- **判别模型**：给你一张图，判断是不是狗（做选择题）
- **生成模型**：给你描述，画一只狗（做开放题）

**关键区别**：判别模型建模 `p(y|x)`，生成模型建模 `p(x)` 或 `p(x|y)`。

### 7. Probability Density（概率密度）

**一句话解释**：描述某个值出现可能性的函数。

**通俗类比**：在"所有可能的狗图"构成的空间里，越像真的狗的地方密度越高，越不像的地方密度越低。生成模型的目标就是学会这个密度函数。

### 8. i.i.d. Samples（独立同分布样本）

**一句话解释**：从同一个分布中独立抽取的样本。

**通俗类比**：就像从同一桶水里舀水，每次舀的一勺都是独立的，但都来自同一桶水。数据集假设就是这样的：每张图片都独立来自"真实图像分布"。

### 9. Conditional Distribution（条件分布）

**一句话解释**：在给定某些条件下的概率分布。

**通俗类比**：
- **无条件生成**：随机画一只动物（可能是狗、猫、鸟……）
- **条件生成**：给定"狗"这个条件，画一只狗

### 10. Guidance（引导）

**一句话解释**：控制生成模型按照特定条件（如文本描述）生成内容。

**关键方法**：Classifier-Free Guidance（无分类器引导）——不训练额外的分类器，直接在生成过程中调整条件和非条件输出的差异。

---

## 🤖 与 NanoHermes / AI Agent 的呼应

| 概念 | AI Agent 中的应用 |
|------|------------------|
| **从噪声到数据** | Agent 从模糊的用户意图中"生成"精确的代码/操作 |
| **迭代优化** | 类似扩散模型的多步去噪，Agent 也是多轮对话逐步 refine 结果 |
| **条件生成** | 用户 prompt → Agent 输出，本质是条件分布采样 |
| **Score Matching** | Agent 的"直觉"——判断当前状态离目标还有多远，往哪个方向调整 |

**生成 = 从一个你看不见、只有样本的分布里，学会重新采样。**

这句话同样适用于 AI Agent：用户看不到模型的"思维分布"，但通过交互（样本），Agent 学会了在正确的位置"采样"出有用的回答。
