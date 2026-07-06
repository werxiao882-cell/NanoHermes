# Stanford CME 296 - Lecture 5: Image Generation Architectures (U-Net, DiT)

> **课程**: Stanford CME 296 - Diffusion & Large Vision Models
> **讲师**: Afshine Amidi & Shervine Amidi
> **视频**: [YouTube 1:46:26](https://www.youtube.com/watch?v=HpFdSlMeXzQ&list=PLoROMvodv4rNdy8rt2rZ4T2xM0OjADnfu&index=5)
> **Slides PDF**: [spring26-cme296-lecture5.pdf](../spring26-cme296-lecture5.pdf)
> **总页数**: 171 页幻灯片

---

## Slide 1

![Slide 1](images/lec5_p001.png)

### 幻灯片内容

CME 296: Diﬀusion &
Large Vision Models
Afshine Amidi & Shervine Amidi
Lecture 5

### 通俗解释

Lecture 5 封面：图像生成架构（Image Generation Architectures）。讨论扩散模型使用的网络架构。

---

## Slide 2

![Slide 2](images/lec5_p002.png)

### 幻灯片内容

Recap of last episodes…
Lectures 1, 2, 3
Generation paradigms
Diﬀusion
Score 
matching
Flow 
matching

### 通俗解释

回顾前几讲：Lecture 1-3 介绍了三种生成范式（Diffusion/Score Matching/Flow Matching）。

---

## Slide 3

![Slide 3](images/lec5_p003.png)

### 幻灯片内容

Recap of last episodes…
Lectures 1, 2, 3
Generation paradigms
Lecture 4
Latent space, guidance
Diﬀusion
Score 
matching
Flow 
matching
Encoder
Decoder
Latent 
space
Variational AutoEncoder (VAE)

### 通俗解释

回顾 Lecture 4：潜空间（VAE）、文本表示（CLIP）、引导（CFG）。

---

## Slide 4

![Slide 4](images/lec5_p004.png)

### 幻灯片内容

Today's lecture
A teddy bear 
reading a book
Generation 
model
Today's lecture: Image generation architectures
Model architecture

### 通俗解释

今天的内容：卷积、U-Net、Attention 机制、Diffusion Transformers (DiT)、多模态 DiT、优化。

---

## Slide 5

![Slide 5](images/lec5_p005.png)

### 幻灯片内容

Motivation
U-Net
Diﬀusion Transformer
End-to-end example
Multimodal DiT
Optimizations
Diﬀusion & 
Large Vision 
Models

### 通俗解释

动机：不同的网络架构如何影响扩散模型的性能和质量？

---

## Slide 6

![Slide 6](images/lec5_p006.png)

### 幻灯片内容

Problem statement
Generation 
model
Noise level 
Condition
A teddy bear 
reading a book
Noisy latent
Velocity

### 通俗解释

问题陈述：给定噪声图像和时间步，如何设计网络来预测噪声？

---

## Slide 7

![Slide 7](images/lec5_p007.png)

### 幻灯片内容

Objective of this lecture
Generation 
model
Noise level 
Condition
A teddy bear 
reading a book
Noisy latent
Velocity

### 通俗解释

本讲目标：理解 U-Net 和 DiT 这两种主流架构的原理和优劣。

---

## Slide 8

![Slide 8](images/lec5_p008.png)

### 幻灯片内容

Side notes
Generation 
model
Noise level 
Condition
A teddy bear 
reading a book
Noisy latent
Velocity

### 通俗解释

旁注：U-Net 最初用于生物医学图像分割，后来被扩散模型采用。

---

## Slide 9

![Slide 9](images/lec5_p009.png)

### 幻灯片内容

Side notes
Generation 
model
Noise level 
Condition
Make this teddy 
bear dance
Noisy latent
Velocity
Could also be:

### 通俗解释

旁注继续：DiT 是 2022 年提出的，用 Transformer 替代 U-Net 作为扩散模型的骨干网络。

---

## Slide 10

![Slide 10](images/lec5_p010.png)

### 幻灯片内容

Side notes
Generation 
model
Noise level 
Condition
A teddy bear 
reading a book
Noisy latent
Velocity

### 通俗解释

旁注继续：DiT 在可扩展性方面表现更好，适合大规模训练。

---

## Slide 11

![Slide 11](images/lec5_p011.png)

### 幻灯片内容

Side notes
Generation 
model
Noise level 
Condition
A teddy bear 
reading a book
Noisy latent
Noise
Score
Velocity
Could also be:

### 通俗解释

旁注继续：本讲不涉及具体实现细节，聚焦架构设计理念。

---

## Slide 12

![Slide 12](images/lec5_p012.png)

### 幻灯片内容

Goal
Objective. Choose architecture for image generation with criteria below:
●
Understand global structure
●
Preserve local details
●
Responsive to external signals (timestep, condition)
●
Scalable computationally

### 通俗解释

目标：理解为什么 U-Net 和 DiT 适合扩散模型。

---

## Slide 13

![Slide 13](images/lec5_p013.png)

### 幻灯片内容

Motivation
U-Net
Diﬀusion Transformer
End-to-end example
Multimodal DiT
Optimizations
Diﬀusion & 
Large Vision 
Models

### 通俗解释

动机回顾：扩散模型需要一个能处理多尺度信息的网络。

---

## Slide 14

![Slide 14](images/lec5_p014.png)

### 通俗解释

过渡页或标题页。

---

## Slide 15

![Slide 15](images/lec5_p015.png)

### 通俗解释

过渡页或标题页。

---

## Slide 16

![Slide 16](images/lec5_p016.png)

### 通俗解释

过渡页或标题页。

---

## Slide 17

![Slide 17](images/lec5_p017.png)

### 幻灯片内容

Intuition behind convolution-based models
Idea. Mimic human vision via "inductive" bias baked into the model

### 通俗解释

基于卷积的模型的直觉：卷积能捕获局部特征，适合图像处理。

---

## Slide 18

![Slide 18](images/lec5_p018.png)

### 幻灯片内容

Convolution operation with ﬁlters
VIP cheatsheets on Convolutional Neural Networks, Amidi, 2018.
Convolution ﬁlter. Feature detector
Filter
Feature map
Activation map
aka
Input
e.g. edges, corners, textures, patterns, shapes

### 通俗解释

卷积操作：滤波器（filter）在图像上滑动，计算局部区域的加权和。

---

## Slide 19

![Slide 19](images/lec5_p019.png)

### 幻灯片内容

Convolution operation with ﬁlters
VIP cheatsheets on Convolutional Neural Networks, Amidi, 2018.
Filter. Performs convolution operations on the input.

### 通俗解释

卷积操作继续：不同的滤波器提取不同的特征（边缘、纹理等）。

---

## Slide 20

![Slide 20](images/lec5_p020.png)

### 幻灯片内容

Convolution operation with ﬁlters
VIP cheatsheets on Convolutional Neural Networks, Amidi, 2018.
Filter. Performs convolution operations on the input.
Stride. Amount by which the ﬁlter moves.

### 通俗解释

卷积操作继续：堆叠卷积层可以学习越来越复杂的特征。

---

## Slide 21

![Slide 21](images/lec5_p021.png)

### 幻灯片内容

Receptive ﬁeld
Receptive ﬁeld. Area that the activation map can "see"
VIP cheatsheets on Convolutional Neural Networks, Amidi, 2018.

### 通俗解释

感受野（Receptive Field）：一个输出像素能看到的输入区域大小。

---

## Slide 22

![Slide 22](images/lec5_p022.png)

### 幻灯片内容

Receptive ﬁeld
Receptive ﬁeld. Area that the activation map can "see"
VIP cheatsheets on Convolutional Neural Networks, Amidi, 2018.
A pixel can see an area of 
where
Filter 
size
Stride

### 通俗解释

感受野继续：深层网络有更大的感受野，能捕获更全局的信息。

---

## Slide 23

![Slide 23](images/lec5_p023.png)

### 幻灯片内容

Downsampling with pooling operation
Pooling. Downsampling operation, per channel. Typically after convolution.
VIP cheatsheets on Convolutional Neural Networks, Amidi, 2018.
Average pooling
Max pooling

### 通俗解释

下采样（Pooling）：减小特征图尺寸，增大感受野，减少计算量。

---

## Slide 24

![Slide 24](images/lec5_p024.png)

### 幻灯片内容

Upsampling with transpose convolution
Input
feature map
Upsampled 
feature map
Transpose convolution. Upsampling operation, equivalent of "broadcasting"

### 通俗解释

上采样（Transpose Convolution）：增大特征图尺寸，用于重建图像。

---

## Slide 25

![Slide 25](images/lec5_p025.png)

### 幻灯片内容

Proposal of a convolution-based architecture
U-Net: Convolutional Networks for Biomedical Image Segmentation, Ronneberger et al., 2015.
●
Captures both local and global 
features
●
Inductive bias that is relevant to 
reverse diﬀusion process
●
Same dimensions for input / output
Overview

### 通俗解释

基于卷积的架构提案：编码器-解码器结构，中间有跳跃连接。

---

## Slide 26

![Slide 26](images/lec5_p026.png)

### 幻灯片内容

U-Net: convolution-based architecture
-Net
Figure adapted from U-Net: Convolutional Networks for Biomedical Image Segmentation, Ronneberger et al., 2015.

### 通俗解释

U-Net 架构：因形状像 U 而得名。左侧下采样，右侧上采样，中间有跳跃连接。

---

## Slide 27

![Slide 27](images/lec5_p027.png)

### 幻灯片内容

U-Net: downsampling phase
Figure adapted from U-Net: Convolutional Networks for Biomedical Image Segmentation, Ronneberger et al., 2015.
Downsampling
●
Mix of convolution and max pooling
●
Number of features is halved at each 
step
●
Extraction of relevant features
●
Similar to an "Encoder"

### 通俗解释

U-Net 下采样阶段：逐步减小特征图尺寸，增加通道数，提取抽象特征。

---

## Slide 28

![Slide 28](images/lec5_p028.png)

### 幻灯片内容

U-Net: upsampling phase
Figure adapted from U-Net: Convolutional Networks for Biomedical Image Segmentation, Ronneberger et al., 2015.
●
Mix of up-convolution and 
convolutions
●
Number of features is doubled at 
each step
●
1x1 convolution at the last step 
before obtaining output
●
Similar to a "Decoder"
Upsampling

### 通俗解释

U-Net 上采样阶段：逐步增大特征图尺寸，减少通道数，重建图像。

---

## Slide 29

![Slide 29](images/lec5_p029.png)

### 幻灯片内容

Figure adapted from U-Net: Convolutional Networks for Biomedical Image Segmentation, Ronneberger et al., 2015.
●
Avoids losing local information
●
"Highway" of information
U-Net: residual connections
"Copy and crop" connections

### 通俗解释

U-Net 示意图：跳跃连接将下采样的特征直接传到对应的上采样层，保留细节信息。

---

## Slide 30

![Slide 30](images/lec5_p030.png)

### 幻灯片内容

Figure adapted from U-Net: Convolutional Networks for Biomedical Image Segmentation, Ronneberger et al., 2015.
U-Net: adding condition information
How can we add 
time and class label 
information?

### 通俗解释

U-Net 跳跃连接的作用：防止信息丢失，让网络能同时利用局部和全局特征。

---

## Slide 31

![Slide 31](images/lec5_p031.png)

### 幻灯片内容

Representation of timestep
12
3
6
9
10
11
1
2
8
7
4
5
Hour (slow)
Minute (fast)
Second (very fast)

### 通俗解释

时间步表示：如何将时间步 t 输入到网络？使用正弦位置编码（sinusoidal embedding）。

---

## Slide 32

![Slide 32](images/lec5_p032.png)

### 幻灯片内容

Representation of timestep
+1
-1
Dimension
Timestep
Figure adapted from Transformer Architecture: The Positional Encoding, Kazemnejad, 2019.
12
3
6
9
10
11
1
2
8
7
4
5
Hour (slow)
Minute (fast)
Second (very fast)

### 通俗解释

时间步表示继续：类似于 Transformer 中的位置编码，将标量 t 映射为向量。

---

## Slide 33

![Slide 33](images/lec5_p033.png)

### 幻灯片内容

Representation of class label
teddy bear
Vector
●
Embedding corresponding to predeﬁned class
Predeﬁned class

### 通俗解释

类别标签表示：对于条件生成（如生成特定类别的图像），需要表示类别信息。

---

## Slide 34

![Slide 34](images/lec5_p034.png)

### 幻灯片内容

Representation of class label
teddy bear
Vector
●
Embedding corresponding to predeﬁned class
●
Rich embeddings from a pretrained LLM
a
Vectors
teddy
bear
is
reading
Predeﬁned class
Freeform text

### 通俗解释

类别标签表示继续：使用 embedding 层将类别索引映射为向量。

---

## Slide 35

![Slide 35](images/lec5_p035.png)

### 幻灯片内容

Figure adapted from U-Net: Convolutional Networks for Biomedical Image Segmentation, Ronneberger et al., 2015.
Method 1
U-Net: adding condition information
Added to the feature map

### 通俗解释

U-Net 在扩散模型中的应用：原始 DDPM 就使用了 U-Net 架构。

---

## Slide 36

![Slide 36](images/lec5_p036.png)

### 幻灯片内容

Figure adapted from U-Net: Convolutional Networks for Biomedical Image Segmentation, Ronneberger et al., 2015.
Method 1
U-Net: adding condition information
Added to the feature map
Method 2
Modulate feature map via scaling / 
shifting

### 通俗解释

U-Net 修改：扩散模型中的 U-Net 需要接收时间步作为额外输入。

---

## Slide 37

![Slide 37](images/lec5_p037.png)

### 幻灯片内容

Figure adapted from U-Net: Convolutional Networks for Biomedical Image Segmentation, Ronneberger et al., 2015.
Method 1
U-Net: adding condition information
Added to the feature map
Method 2
Modulate feature map via scaling / 
shifting
Method 3
Cross-attention of condition with 
feature map

### 通俗解释

U-Net 修改继续：时间步信息通过归一化层注入到网络中。

---

## Slide 38

![Slide 38](images/lec5_p038.png)

### 幻灯片内容

Timeline of U-Net-based models
Original 
U-Net
2015
2020
U-Net in pixel space 
with DDPM
2021
2022
U-Net in latent space 
with LDM
2023
Big U-Net with
Stable Diﬀusion XL
Note: This timeline is not meant to be exhaustive in any way.

### 通俗解释

基于 U-Net 的模型时间线：DDPM (2020) -> Improved DDPM -> GLIDE -> DALL-E 2 -> Stable Diffusion。

---

## Slide 39

![Slide 39](images/lec5_p039.png)

### 幻灯片内容

Timeline of U-Net-based models
Original 
U-Net
2015
2020
2021
2022
U-Net in latent space 
with LDM
2023
Transformer
Vision Transformer
Note: This timeline is not meant to be exhaustive in any way.
Big U-Net with
Stable Diﬀusion XL
U-Net in pixel space 
with DDPM

### 通俗解释

时间线继续：U-Net 架构在扩散模型领域统治了很长时间。

---

## Slide 40

![Slide 40](images/lec5_p040.png)

### 幻灯片内容

Motivation
U-Net
Diﬀusion Transformer
End-to-end example
Multimodal DiT
Optimizations
Diﬀusion & 
Large Vision 
Models

### 通俗解释

动机转变：Transformer 在 NLP 中取得成功，能否用于视觉生成？

---

## Slide 41

![Slide 41](images/lec5_p041.png)

### 幻灯片内容

Motivating example
Image generated with ChatGPT, May 5th, 2026.
Need to preserve local details 
across long distances

### 通俗解释

 motivating example：ViT（Vision Transformer）证明了 Transformer 可以用于图像理解。

---

## Slide 42

![Slide 42](images/lec5_p042.png)

### 幻灯片内容

Attention mechanism
Attention Is All You Need, Vaswani et al., 2017. Figure from Super Study Guide: Transformers & LLMs, Amidi, 2024.
Idea. Remove inductive bias

### 通俗解释

Attention 机制：核心思想是让每个位置关注其他所有位置，捕获全局依赖。

---

## Slide 43

![Slide 43](images/lec5_p043.png)

### 幻灯片内容

Attention mechanism
Attention Is All You Need, Vaswani et al., 2017. Figure from Super Study Guide: Transformers & LLMs, Amidi, 2024.
Idea. Remove inductive bias

### 通俗解释

Attention 继续：Self-attention 计算 query-key-value 的交互。

---

## Slide 44

![Slide 44](images/lec5_p044.png)

### 幻灯片内容

Attention mechanism
Attention Is All You Need, Vaswani et al., 2017. Figure from Super Study Guide: Transformers & LLMs, Amidi, 2024.
Idea. Remove inductive bias

### 通俗解释

Attention 公式：Attention(Q,K,V) = softmax(QK^T / sqrt(d)) V。

---

## Slide 45

![Slide 45](images/lec5_p045.png)

### 幻灯片内容

Transformer
Figures from Attention Is All You Need, Vaswani et al., 2017. Detailed explanations in Stanford's CME 295: Transformers and LLMs.
Multi-head 
attention layer
Transformer 
architecture

### 通俗解释

Transformer：由多个 self-attention 层和前馈网络组成。

---

## Slide 46

![Slide 46](images/lec5_p046.png)

### 幻灯片内容

Transformer for vision understanding…
An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale, Dosovitskiy et al., 2020.
ViT = Vision Transformer

### 通俗解释

视觉理解的 Transformer：ViT 将图像分块，用 Transformer 处理。

---

## Slide 47

![Slide 47](images/lec5_p047.png)

### 幻灯片内容

…and Transformer for vision generation!
DiT = Diﬀusion Transformer
Scalable Diﬀusion Models with Transformers, Peebles et al., 2022.

### 通俗解释

视觉生成的 Transformer：DiT 将 Transformer 用于扩散模型。

---

## Slide 48

![Slide 48](images/lec5_p048.png)

### 幻灯片内容

DiT: tokenization of the input via patches
Figures adapted from Scalable Diﬀusion Models with Transformers, Peebles et al., 2022.
Noised 
latent
Patchify
Input 
tokens

### 通俗解释

DiT tokenization：将输入图像分成 patches，每个 patch 作为一个 token。

---

## Slide 49

![Slide 49](images/lec5_p049.png)

### 幻灯片内容

DiT: embedding of conditions
+1
-1
Dimension
Position
Timestep 
embedding
Label 
embedding
teddy bear
Vector
Figures adapted from Scalable Diﬀusion Models with Transformers, Peebles et al., 2022 and Transformer Architecture: The Positional Encoding, 
Kazemnejad, 2019.

### 通俗解释

DiT 条件嵌入：将文本等条件信息嵌入为向量。

---

## Slide 50

![Slide 50](images/lec5_p050.png)

### 幻灯片内容

DiT: injecting conditions with adaptive layer norm
Adaptive Layer Norm
Figures adapted from Scalable Diﬀusion Models with Transformers, Peebles et al., 2022.

### 通俗解释

DiT 条件注入：使用自适应层归一化（AdaLN）将条件注入到 Transformer 中。

---

## Slide 51

![Slide 51](images/lec5_p051.png)

### 幻灯片内容

DiT: injecting conditions with cross-attention
Adaptive Layer Norm
Cross-attention
Figures adapted from Scalable Diﬀusion Models with Transformers, Peebles et al., 2022.

### 通俗解释

DiT 条件注入：也可以使用 cross-attention 注入条件。

---

## Slide 52

![Slide 52](images/lec5_p052.png)

### 幻灯片内容

DiT: injecting conditions with in-context conditioning
Adaptive Layer Norm
Cross-attention
In-context conditioning
Figures adapted from Scalable Diﬀusion Models with Transformers, Peebles et al., 2022.

### 通俗解释

DiT 条件注入：还可以使用 in-context conditioning（类似 LLM 的方式）。

---

## Slide 53

![Slide 53](images/lec5_p053.png)

### 幻灯片内容

DiT: comparison of diﬀerent condition injections
🥇
🥈
🥉
Adaptive Layer Norm
Cross-attention
In-context conditioning
Figure from Scalable Diﬀusion Models with Transformers, Peebles et al., 2022.

### 通俗解释

不同条件注入方式比较：AdaLN、cross-attention、in-context 各有优劣。

---

## Slide 54

![Slide 54](images/lec5_p054.png)

### 幻灯片内容

DiT: comparison of diﬀerent condition injections
🥇
🥈
🥉
Adaptive Layer Norm
Cross-attention
In-context conditioning
Figure from Scalable Diﬀusion Models with Transformers, Peebles et al., 2022.

### 通俗解释

比较继续：AdaLN 计算效率高，cross-attention 表达能力强。

---

## Slide 55

![Slide 55](images/lec5_p055.png)

### 幻灯片内容

Intuition behind adaptive layer norm
Representation of a 
patch embedding

### 通俗解释

自适应层归一化（AdaLN）直觉：用条件信息调制归一化的缩放和平移参数。

---

## Slide 56

![Slide 56](images/lec5_p056.png)

### 幻灯片内容

Intuition behind adaptive layer norm
brown color
round shape
ﬂuﬀ local details
white color

### 通俗解释

AdaLN 继续：标准层归一化有固定的 gamma 和 beta，AdaLN 让它们依赖于条件。

---

## Slide 57

![Slide 57](images/lec5_p057.png)

### 幻灯片内容

Intuition behind adaptive layer norm
brown fluffy teddy bear
a lot of noise
brown color
round shape
ﬂuﬀ local details
white color
Conditions
Need to focus on global structure 
since at the early stage of generation.

### 通俗解释

AdaLN 公式：AdaLN(x, c) = gamma(c) * LayerNorm(x) + beta(c)。

---

## Slide 58

![Slide 58](images/lec5_p058.png)

### 幻灯片内容

Intuition behind adaptive layer norm
brown fluffy teddy bear
brown color
round shape
ﬂuﬀ local details
white color
Conditions
almost no noise
Need to focus on local details since 
almost arriving at the ﬁnal image.

### 通俗解释

AdaLN 优势：简单高效，不需要额外的 attention 计算。

---

## Slide 59

![Slide 59](images/lec5_p059.png)

### 幻灯片内容

Adaptive layer normalization
Idea. "Modulate" vector with respect to conditions (timestep and class label)

### 通俗解释

这页内容：Adaptive layer normalization Idea. "Modulate" vector with respect to conditions ...

---

## Slide 60

![Slide 60](images/lec5_p060.png)

### 幻灯片内容

Adaptive layer normalization
Idea. "Modulate" vector with respect to conditions (timestep and class label)
1. Determine intensity of modulation as a function of conditions
Steps.
Timestep
Class label
Projection
Vectors

### 通俗解释

这页内容：Adaptive layer normalization Idea. "Modulate" vector with respect to conditions ...

---

## Slide 61

![Slide 61](images/lec5_p061.png)

### 幻灯片内容

Adaptive layer normalization
Idea. "Modulate" vector with respect to conditions (timestep and class label)
1. Determine intensity of modulation as a function of conditions
2. Modulate token with quantities
Steps.

### 通俗解释

这页内容：Adaptive layer normalization Idea. "Modulate" vector with respect to conditions ...

---

## Slide 62

![Slide 62](images/lec5_p062.png)

### 幻灯片内容

Adaptive layer normalization
Idea. "Modulate" vector with respect to conditions (timestep and class label)
1. Determine intensity of modulation as a function of conditions
2. Modulate token with quantities
Steps.

### 通俗解释

这页内容：Adaptive layer normalization Idea. "Modulate" vector with respect to conditions ...

---

## Slide 63

![Slide 63](images/lec5_p063.png)

### 幻灯片内容

Adaptive layer normalization
Idea. "Modulate" vector with respect to conditions (timestep and class label)
1. Determine intensity of modulation as a function of conditions
2. Modulate token with quantities
Steps.

### 通俗解释

这页内容：Adaptive layer normalization Idea. "Modulate" vector with respect to conditions ...

---

## Slide 64

![Slide 64](images/lec5_p064.png)

### 幻灯片内容

Adaptive layer normalization
Idea. "Modulate" vector with respect to conditions (timestep and class label)
1. Determine intensity of modulation as a function of conditions
2. Modulate token with quantities
Steps.

### 通俗解释

这页内容：Adaptive layer normalization Idea. "Modulate" vector with respect to conditions ...

---

## Slide 65

![Slide 65](images/lec5_p065.png)

### 幻灯片内容

Adaptive layer normalization
Idea. "Modulate" vector with respect to conditions (timestep and class label)
1. Determine intensity of modulation as a function of conditions
2. Modulate token with quantities
Steps.

### 通俗解释

这页内容：Adaptive layer normalization Idea. "Modulate" vector with respect to conditions ...

---

## Slide 66

![Slide 66](images/lec5_p066.png)

### 幻灯片内容

Adaptive layer normalization
Idea. "Modulate" vector with respect to conditions (timestep and class label)
1. Determine intensity of modulation as a function of conditions
2. Modulate token with quantities
Steps.

### 通俗解释

这页内容：Adaptive layer normalization Idea. "Modulate" vector with respect to conditions ...

---

## Slide 67

![Slide 67](images/lec5_p067.png)

### 幻灯片内容

Adaptive layer normalization
Idea. "Modulate" vector with respect to conditions (timestep and class label)
1. Determine intensity of modulation as a function of conditions
2. Modulate token with quantities
Steps.

### 通俗解释

这页内容：Adaptive layer normalization Idea. "Modulate" vector with respect to conditions ...

---

## Slide 68

![Slide 68](images/lec5_p068.png)

### 幻灯片内容

Adaptive layer normalization
Idea. "Modulate" vector with respect to conditions (timestep and class label)
1. Determine intensity of modulation as a function of conditions
2. Modulate token with quantities
Steps.

### 通俗解释

这页内容：Adaptive layer normalization Idea. "Modulate" vector with respect to conditions ...

---

## Slide 69

![Slide 69](images/lec5_p069.png)

### 幻灯片内容

Adaptive layer normalization
Idea. "Modulate" vector with respect to conditions (timestep and class label)
1. Determine intensity of modulation as a function of conditions
2. Modulate token with quantities
Steps.
element-wise multiplication

### 通俗解释

这页内容：Adaptive layer normalization Idea. "Modulate" vector with respect to conditions ...

---

## Slide 70

![Slide 70](images/lec5_p070.png)

### 幻灯片内容

Adaptive layer normalization
Idea. "Modulate" vector with respect to conditions (timestep and class label)
1. Determine intensity of modulation as a function of conditions
2. Modulate token with quantities
Steps.
Gate
Scale
Shift

### 通俗解释

这页内容：Adaptive layer normalization Idea. "Modulate" vector with respect to conditions ...

---

## Slide 71

![Slide 71](images/lec5_p071.png)

### 幻灯片内容

Adaptive layer normalization
Idea. "Modulate" vector with respect to conditions (timestep and class label)
1. Determine intensity of modulation as a function of conditions
2. Modulate token with quantities
Steps.
At the beginning:
adaLN-Zero

### 通俗解释

这页内容：Adaptive layer normalization Idea. "Modulate" vector with respect to conditions ...

---

## Slide 72

![Slide 72](images/lec5_p072.png)

### 幻灯片内容

●
Gate
DiT: injection of conditions with adaLN-Zero
Modulation of representation with:
Figures adapted from Scalable Diﬀusion Models with Transformers, Peebles et al., 2022.
●
Scale
●
Shift
as a function of

### 通俗解释

这页内容：● Gate DiT: injection of conditions with adaLN-Zero Modulation of representation...

---

## Slide 73

![Slide 73](images/lec5_p073.png)

### 幻灯片内容

DiT: reformatting the output
Tokens
Linear and Reshape
Noise
Diagonal 
covariance
Layer Norm
Figures adapted from Scalable Diﬀusion Models with Transformers, Peebles et al., 2022.

### 通俗解释

这页内容：DiT: reformatting the output Tokens Linear and Reshape Noise Diagonal  covarianc...

---

## Slide 74

![Slide 74](images/lec5_p074.png)

### 幻灯片内容

Scaling up DiT…
Figures from Scalable Diﬀusion Models with Transformers, Peebles et al., 2022.
●
Number of parameters is not enough to quantify model complexity
●
FLoating-point OPerations (FLOPs) = # operations in forward pass
●
Smaller patch size corresponds to higher FLOPs

### 通俗解释

这页内容：Scaling up DiT… Figures from Scalable Diﬀusion Models with Transformers, Peebles...

---

## Slide 75

![Slide 75](images/lec5_p075.png)

### 幻灯片内容

Scaling up DiT… improves results!
Figures from Scalable Diﬀusion Models with Transformers, Peebles et al., 2022.

### 通俗解释

这页内容：Scaling up DiT… improves results! Figures from Scalable Diﬀusion Models with Tra...

---

## Slide 76

![Slide 76](images/lec5_p076.png)

### 幻灯片内容

Motivation
U-Net
Diﬀusion Transformer
End-to-end example
Multimodal DiT
Optimizations
Diﬀusion & 
Large Vision 
Models

### 通俗解释

这页内容：Motivation U-Net Diﬀusion Transformer End-to-end example Multimodal DiT Optimiza...

---

## Slide 77

![Slide 77](images/lec5_p077.png)

### 幻灯片内容

Let's go through an end-to-end example together!
Image 
generation 
model
teddy bear

### 通俗解释

这页内容：Let's go through an end-to-end example together! Image  generation  model teddy ...

---

## Slide 78

![Slide 78](images/lec5_p078.png)

### 幻灯片内容

Sample a noisy latent
Latent space
learned by the VAE

### 通俗解释

这页内容：Sample a noisy latent Latent space learned by the VAE...

---

## Slide 79

![Slide 79](images/lec5_p079.png)

### 幻灯片内容

Patchify noisy latent
patches
Divide

### 通俗解释

这页内容：Patchify noisy latent patches Divide...

---

## Slide 80

![Slide 80](images/lec5_p080.png)

### 幻灯片内容

Patchify noisy latent
Patch
Patch embedding 
Perform projection

### 通俗解释

这页内容：Patchify noisy latent Patch Patch embedding  Perform projection...

---

## Slide 81

![Slide 81](images/lec5_p081.png)

### 幻灯片内容

Embed conditions
Timestep 
embedding
Label 
embedding
Condition 
embedding

### 通俗解释

这页内容：Embed conditions Timestep  embedding Label  embedding Condition  embedding...

---

## Slide 82

![Slide 82](images/lec5_p082.png)

### 幻灯片内容

Attention layers with noisy latent

### 通俗解释

这页内容：Attention layers with noisy latent...

---

## Slide 83

![Slide 83](images/lec5_p083.png)

### 幻灯片内容

Attention layers with noisy latent

### 通俗解释

这页内容：Attention layers with noisy latent...

---

## Slide 84

![Slide 84](images/lec5_p084.png)

### 幻灯片内容

Attention layers with noisy latent
Patch embedding

### 通俗解释

这页内容：Attention layers with noisy latent Patch embedding...

---

## Slide 85

![Slide 85](images/lec5_p085.png)

### 幻灯片内容

Attention layers with noisy latent
Position embedding
Patch embedding

### 通俗解释

这页内容：Attention layers with noisy latent Position embedding Patch embedding...

---

## Slide 86

![Slide 86](images/lec5_p086.png)

### 幻灯片内容

Attention layers with noisy latent
Position-aware patch embedding

### 通俗解释

这页内容：Attention layers with noisy latent Position-aware patch embedding...

---

## Slide 87

![Slide 87](images/lec5_p087.png)

### 幻灯片内容

Attention layers with noisy latent
Position-aware patch embeddings

### 通俗解释

这页内容：Attention layers with noisy latent Position-aware patch embeddings...

---

## Slide 88

![Slide 88](images/lec5_p088.png)

### 幻灯片内容

Attention layers with noisy latent
Position-aware patch 
embeddings matrix

### 通俗解释

这页内容：Attention layers with noisy latent Position-aware patch  embeddings matrix...

---

## Slide 89

![Slide 89](images/lec5_p089.png)

### 幻灯片内容

Attention layers with noisy latent
Position-aware patch 
embeddings matrix

### 通俗解释

这页内容：Attention layers with noisy latent Position-aware patch  embeddings matrix...

---

## Slide 90

![Slide 90](images/lec5_p090.png)

### 幻灯片内容

Attention layers with noisy latent
Condition embedding
Position-aware patch 
embeddings matrix

### 通俗解释

这页内容：Attention layers with noisy latent Condition embedding Position-aware patch  emb...

---

## Slide 91

![Slide 91](images/lec5_p091.png)

### 幻灯片内容

Attention layers with noisy latent
Condition embedding
Position-aware patch 
embeddings matrix
DIFFUSION TRANSFORMER BLOCK

### 通俗解释

这页内容：Attention layers with noisy latent Condition embedding Position-aware patch  emb...

---

## Slide 92

![Slide 92](images/lec5_p092.png)

### 幻灯片内容

Process condition embeddings
Condition embedding
Position-aware patch 
embeddings matrix

### 通俗解释

这页内容：Process condition embeddings Condition embedding Position-aware patch  embedding...

---

## Slide 93

![Slide 93](images/lec5_p093.png)

### 幻灯片内容

Process condition embeddings
Condition embedding
Position-aware patch 
embeddings matrix
MLP layer

### 通俗解释

这页内容：Process condition embeddings Condition embedding Position-aware patch  embedding...

---

## Slide 94

![Slide 94](images/lec5_p094.png)

### 幻灯片内容

Obtain gate from conditions
Condition embedding
Position-aware patch 
embeddings matrix
MLP layer
Gate

### 通俗解释

这页内容：Obtain gate from conditions Condition embedding Position-aware patch  embeddings...

---

## Slide 95

![Slide 95](images/lec5_p095.png)

### 幻灯片内容

Obtain scale from conditions
Condition embedding
Position-aware patch 
embeddings matrix
MLP layer
Gate
Scale

### 通俗解释

这页内容：Obtain scale from conditions Condition embedding Position-aware patch  embedding...

---

## Slide 96

![Slide 96](images/lec5_p096.png)

### 幻灯片内容

Obtain shift from conditions
Condition embedding
Position-aware patch 
embeddings matrix
MLP layer
Gate
Shift
Scale

### 通俗解释

这页内容：Obtain shift from conditions Condition embedding Position-aware patch  embedding...

---

## Slide 97

![Slide 97](images/lec5_p097.png)

### 幻灯片内容

Obtain quantities from condition
Condition embedding
Position-aware patch 
embeddings matrix
MLP layer
Gate
Shift
Scale

### 通俗解释

这页内容：Obtain quantities from condition Condition embedding Position-aware patch  embed...

---

## Slide 98

![Slide 98](images/lec5_p098.png)

### 幻灯片内容

Process patch embeddings
Condition embedding
Position-aware patch 
embeddings matrix
MLP layer
Gate
Shift
Scale

### 通俗解释

这页内容：Process patch embeddings Condition embedding Position-aware patch  embeddings ma...

---

## Slide 99

![Slide 99](images/lec5_p099.png)

### 幻灯片内容

Process patch embeddings through attention
Condition embedding
Position-aware patch 
embeddings matrix
Normalize
MLP layer
Gate
Shift
Scale

### 通俗解释

这页内容：Process patch embeddings through attention Condition embedding Position-aware pa...

---

## Slide 100

![Slide 100](images/lec5_p100.png)

### 幻灯片内容

Process patch embeddings through attention
Condition embedding
Position-aware patch 
embeddings matrix
Normalize
Scale & shift with
MLP layer
Gate
Shift
Scale

### 通俗解释

这页内容：Process patch embeddings through attention Condition embedding Position-aware pa...

---

## Slide 101

![Slide 101](images/lec5_p101.png)

### 幻灯片内容

Process patch embeddings through attention
Condition embedding
Position-aware patch 
embeddings matrix
Self-attention
Normalize
Scale & shift with
MLP layer
Gate
Shift
Scale

### 通俗解释

这页内容：Process patch embeddings through attention Condition embedding Position-aware pa...

---

## Slide 102

![Slide 102](images/lec5_p102.png)

### 幻灯片内容

Process patch embeddings through attention
Condition embedding
Position-aware patch 
embeddings matrix
Self-attention
Scale & shift with
Gate with
MLP layer
Gate
Shift
Scale
Normalize

### 通俗解释

这页内容：Process patch embeddings through attention Condition embedding Position-aware pa...

---

## Slide 103

![Slide 103](images/lec5_p103.png)

### 幻灯片内容

Process patch embeddings through attention
Condition embedding
Position-aware patch 
embeddings matrix
Self-attention
Normalize
Scale & shift with
Gate with
MLP layer
Gate
Shift
Scale

### 通俗解释

这页内容：Process patch embeddings through attention Condition embedding Position-aware pa...

---

## Slide 104

![Slide 104](images/lec5_p104.png)

### 幻灯片内容

Process patch embeddings through attention
Condition embedding
Position-aware patch 
embeddings matrix
Self-attention
MLP layer
Gate
Shift
Scale

### 通俗解释

这页内容：Process patch embeddings through attention Condition embedding Position-aware pa...

---

## Slide 105

![Slide 105](images/lec5_p105.png)

### 幻灯片内容

Process patch embeddings through attention

### 通俗解释

这页内容：Process patch embeddings through attention...

---

## Slide 106

![Slide 106](images/lec5_p106.png)

### 幻灯片内容

Process patch embeddings through FFNN
Condition embedding
Position-aware patch 
embeddings matrix
Self-attention
FFNN
MLP layer
Gate
Shift
Scale

### 通俗解释

这页内容：Process patch embeddings through FFNN Condition embedding Position-aware patch  ...

---

## Slide 107

![Slide 107](images/lec5_p107.png)

### 幻灯片内容

Process patch embeddings through FFNN

### 通俗解释

这页内容：Process patch embeddings through FFNN...

---

## Slide 108

![Slide 108](images/lec5_p108.png)

### 幻灯片内容

Obtain output from DiT block
Condition embedding
Position-aware patch 
embeddings matrix
Self-attention
FFNN
MLP layer
Gate
Shift
Scale
Contextualized 
latent state matrix

### 通俗解释

这页内容：Obtain output from DiT block Condition embedding Position-aware patch  embedding...

---

## Slide 109

![Slide 109](images/lec5_p109.png)

### 幻灯片内容

Project and reshape to desired quantity
Condition embedding
Position-aware patch 
embeddings matrix
Contextualized 
latent state matrix
Self-attention
FFNN
MLP layer
Gate
Shift
Scale
Norm, linear, 
reshape

### 通俗解释

这页内容：Project and reshape to desired quantity Condition embedding Position-aware patch...

---

## Slide 110

![Slide 110](images/lec5_p110.png)

### 幻灯片内容

Project and reshape to desired quantity
Condition embedding
Position-aware patch 
embeddings matrix
Contextualized 
latent state matrix
Self-attention
FFNN
MLP layer
Gate
Shift
Scale
Norm, linear, 
reshape
Predicted velocity

### 通俗解释

这页内容：Project and reshape to desired quantity Condition embedding Position-aware patch...

---

## Slide 111

![Slide 111](images/lec5_p111.png)

### 幻灯片内容

Recap of prediction
DIFFUSION TRANSFORMER
teddy bear
Class label
Timestep
Latent
Predicted velocity

### 通俗解释

这页内容：Recap of prediction DIFFUSION TRANSFORMER teddy bear Class label Timestep Latent...

---

## Slide 112

![Slide 112](images/lec5_p112.png)

### 幻灯片内容

Deduce resulting latent
Latent space
learned by the VAE
Prediction from the DiT

### 通俗解释

这页内容：Deduce resulting latent Latent space learned by the VAE Prediction from the DiT...

---

## Slide 113

![Slide 113](images/lec5_p113.png)

### 幻灯片内容

Deduce resulting latent
Latent space
learned by the VAE
Prediction from the DiT

### 通俗解释

这页内容：Deduce resulting latent Latent space learned by the VAE Prediction from the DiT...

---

## Slide 114

![Slide 114](images/lec5_p114.png)

### 幻灯片内容

Deduce resulting latent
Latent space
learned by the VAE
Prediction from the DiT

### 通俗解释

这页内容：Deduce resulting latent Latent space learned by the VAE Prediction from the DiT...

---

## Slide 115

![Slide 115](images/lec5_p115.png)

### 幻灯片内容

Perform iteration over latents
DIFFUSION TRANSFORMER
teddy bear
Class label
Timestep
Latent
Predicted velocity

### 通俗解释

这页内容：Perform iteration over latents DIFFUSION TRANSFORMER teddy bear Class label Time...

---

## Slide 116

![Slide 116](images/lec5_p116.png)

### 幻灯片内容

Perform iteration over latents
Latent space
learned by the VAE
Prediction from the DiT

### 通俗解释

这页内容：Perform iteration over latents Latent space learned by the VAE Prediction from t...

---

## Slide 117

![Slide 117](images/lec5_p117.png)

### 幻灯片内容

Perform iteration over latents
Latent space
learned by the VAE
Prediction from the DiT

### 通俗解释

这页内容：Perform iteration over latents Latent space learned by the VAE Prediction from t...

---

## Slide 118

![Slide 118](images/lec5_p118.png)

### 幻灯片内容

Perform iteration over latents
Latent space
learned by the VAE
Prediction from the DiT

### 通俗解释

这页内容：Perform iteration over latents Latent space learned by the VAE Prediction from t...

---

## Slide 119

![Slide 119](images/lec5_p119.png)

### 幻灯片内容

Obtain ﬁnal latent
Latent space
learned by the VAE

### 通俗解释

这页内容：Obtain ﬁnal latent Latent space learned by the VAE...

---

## Slide 120

![Slide 120](images/lec5_p120.png)

### 幻灯片内容

Decode latent back into pixel space
Decoder
Pixel space
Latent space
learned by the VAE

### 通俗解释

这页内容：Decode latent back into pixel space Decoder Pixel space Latent space learned by ...

---

## Slide 121

![Slide 121](images/lec5_p121.png)

### 幻灯片内容

Motivation
U-Net
Diﬀusion Transformer
End-to-end example
Multimodal DiT
Optimizations
Diﬀusion & 
Large Vision 
Models

### 通俗解释

这页内容：Motivation U-Net Diﬀusion Transformer End-to-end example Multimodal DiT Optimiza...

---

## Slide 122

![Slide 122](images/lec5_p122.png)

### 幻灯片内容

Intuition: back to the example we had
brown fluffy teddy bear
a lot of noise
brown color
round shape
ﬂuﬀ local details
white color
Conditions
Need to focus on global structure 
since at the early stage of generation.

### 通俗解释

这页内容：Intuition: back to the example we had brown fluffy teddy bear a lot of noise bro...

---

## Slide 123

![Slide 123](images/lec5_p123.png)

### 幻灯片内容

Intuition: back to the example we had
brown fluffy teddy bear
a lot of noise
brown color
round shape
ﬂuﬀ local details
white color
Conditions
Need to focus on global structure 
since at the early stage of generation.

### 通俗解释

这页内容：Intuition: back to the example we had brown fluffy teddy bear a lot of noise bro...

---

## Slide 124

![Slide 124](images/lec5_p124.png)

### 幻灯片内容

Intuition: more subtle text prompt
brown fluffy teddy bear surrounded 
by white walls
a lot of noise
brown color
round shape
ﬂuﬀ local details
white color
Conditions
Need to focus on global structure 
since at the early stage of generation.

### 通俗解释

这页内容：Intuition: more subtle text prompt brown fluffy teddy bear surrounded  by white ...

---

## Slide 125

![Slide 125](images/lec5_p125.png)

### 幻灯片内容

Intuition: more subtle text prompt
brown color
round shape
ﬂuﬀ local details
white color
Limitation. All patch latents are subject to 
same "modulation"

### 通俗解释

这页内容：Intuition: more subtle text prompt brown color round shape ﬂuﬀ local details whi...

---

## Slide 126

![Slide 126](images/lec5_p126.png)

### 幻灯片内容

Intuition: more subtle text prompt
brown color
round shape
ﬂuﬀ local details
white color
Limitation. All patch latents are subject to 
same "modulation"

### 通俗解释

这页内容：Intuition: more subtle text prompt brown color round shape ﬂuﬀ local details whi...

---

## Slide 127

![Slide 127](images/lec5_p127.png)

### 幻灯片内容

Mitigate lack of nuance of previous approach
Keep "modulating" using the timestep embedding
1
Strategy.

### 通俗解释

这页内容：Mitigate lack of nuance of previous approach Keep "modulating" using the timeste...

---

## Slide 128

![Slide 128](images/lec5_p128.png)

### 幻灯片内容

Mitigate lack of nuance of previous approach
Keep "modulating" using the timestep embedding
Do something else to allow for more complex interaction for the condition
1
2
Strategy.
Cross-attention
Joint attention

### 通俗解释

这页内容：Mitigate lack of nuance of previous approach Keep "modulating" using the timeste...

---

## Slide 129

![Slide 129](images/lec5_p129.png)

### 幻灯片内容

Mitigate lack of nuance of previous approach
Keep "modulating" using the timestep embedding
Do something else to allow for more complex interaction for the condition
1
2
Strategy.
Cross-attention
Joint attention

### 通俗解释

这页内容：Mitigate lack of nuance of previous approach Keep "modulating" using the timeste...

---

## Slide 130

![Slide 130](images/lec5_p130.png)

### 幻灯片内容

Intuition behind joint attention
Patch embeddings
Condition embedding
Self-attention layer

### 通俗解释

这页内容：Intuition behind joint attention Patch embeddings Condition embedding Self-atten...

---

## Slide 131

![Slide 131](images/lec5_p131.png)

### 幻灯片内容

MultiModal-Diﬀusion Transformer
MM-DiT = MultiModal-Diﬀusion Transformer
Scaling Rectiﬁed Flow Transformers for High-Resolution Image Synthesis, Esser et al., 2024.
Single-stream
Everyone treated equally
●
Term coined in the Stable Diﬀusion 3 paper published in 2024
●
Relies on joint attention of diﬀerent modalities

### 通俗解释

这页内容：MultiModal-Diﬀusion Transformer MM-DiT = MultiModal-Diﬀusion Transformer Scaling...

---

## Slide 132

![Slide 132](images/lec5_p132.png)

### 幻灯片内容

MultiModal-Diﬀusion Transformer
MM-DiT = MultiModal-Diﬀusion Transformer
Scaling Rectiﬁed Flow Transformers for High-Resolution Image Synthesis, Esser et al., 2024.
Single-stream
Double-stream
Each modality is in its own 
stream
Everyone treated equally
●
Term coined in the Stable Diﬀusion 3 paper published in 2024
●
Relies on joint attention of diﬀerent modalities

### 通俗解释

这页内容：MultiModal-Diﬀusion Transformer MM-DiT = MultiModal-Diﬀusion Transformer Scaling...

---

## Slide 133

![Slide 133](images/lec5_p133.png)

### 幻灯片内容

MultiModal-Diﬀusion Transformer
MM-DiT = MultiModal-Diﬀusion Transformer
Scaling Rectiﬁed Flow Transformers for High-Resolution Image Synthesis, Esser et al., 2024.
Single-stream
Double-stream
Hybrid
Each modality is in its own 
stream
Everyone treated equally
Contains both "single-stream" 
and "double-stream" layer
●
Term coined in the Stable Diﬀusion 3 paper published in 2024
●
Relies on joint attention of diﬀerent modalities

### 通俗解释

这页内容：MultiModal-Diﬀusion Transformer MM-DiT = MultiModal-Diﬀusion Transformer Scaling...

---

## Slide 134

![Slide 134](images/lec5_p134.png)

### 幻灯片内容

"Double-stream" DiT variant: SD3, Qwen-Image
Figure from Qwen-Image Technical Report, Qwen Team, 2025.

### 通俗解释

这页内容："Double-stream" DiT variant: SD3, Qwen-Image Figure from Qwen-Image Technical Re...

---

## Slide 135

![Slide 135](images/lec5_p135.png)

### 幻灯片内容

"Single-stream" DiT variant: Z-Image
Figure from Z-Image: An Eﬃcient Image Generation Foundation Model with Single-Stream Diﬀusion Transformer, Z-Image Team, 2025.

### 通俗解释

这页内容："Single-stream" DiT variant: Z-Image Figure from Z-Image: An Eﬃcient Image Gener...

---

## Slide 136

![Slide 136](images/lec5_p136.png)

### 幻灯片内容

Hybrid approach: FLUX.1 Kontext
Figure from FLUX.1 Kontext: Flow Matching for In-Context Image Generation and Editing in Latent Space, Black Forest Labs, 2025.

### 通俗解释

这页内容：Hybrid approach: FLUX.1 Kontext Figure from FLUX.1 Kontext: Flow Matching for In...

---

## Slide 137

![Slide 137](images/lec5_p137.png)

### 幻灯片内容

Timeline
Diﬀusion 
Transformer
2022
2023
2025
2024
Stable 
Diﬀusion 3
Qwen-Image
Single-stream
Double-stream
2026
Hybrid
FLUX.1
Z-Image
Note: This timeline is not meant to be exhaustive in any way.
"MM-DiT" 
coined

### 通俗解释

这页内容：Timeline Diﬀusion  Transformer 2022 2023 2025 2024 Stable  Diﬀusion 3 Qwen-Image...

---

## Slide 138

![Slide 138](images/lec5_p138.png)

### 幻灯片内容

Motivation
U-Net
Diﬀusion Transformer
End-to-end example
Multimodal DiT
Optimizations
Diﬀusion & 
Large Vision 
Models

### 通俗解释

这页内容：Motivation U-Net Diﬀusion Transformer End-to-end example Multimodal DiT Optimiza...

---

## Slide 139

![Slide 139](images/lec5_p139.png)

### 幻灯片内容

Need for position information
Motivation. Direct links "lose" position info
close
Figure from Super Study Guide: Transformers & Large Language Models, Amidi et al., 2024.

### 通俗解释

这页内容：Need for position information Motivation. Direct links "lose" position info clos...

---

## Slide 140

![Slide 140](images/lec5_p140.png)

### 幻灯片内容

Need for position information
Motivation. Direct links "lose" position info
far
Figure from Super Study Guide: Transformers & Large Language Models, Amidi et al., 2024.

### 通俗解释

这页内容：Need for position information Motivation. Direct links "lose" position info far ...

---

## Slide 141

![Slide 141](images/lec5_p141.png)

### 幻灯片内容

Need for position information
Hope. Dot products convey distance between token representations
"
"

### 通俗解释

这页内容：Need for position information Hope. Dot products convey distance between token r...

---

## Slide 142

![Slide 142](images/lec5_p142.png)

### 幻灯片内容

Absolute positional embeddings
Idea. Add position-speciﬁc embedding to token vector
Figure adapted from Attention Is All You Need, Vaswani et al., 2017.

### 通俗解释

这页内容：Absolute positional embeddings Idea. Add position-speciﬁc embedding to token vec...

---

## Slide 143

![Slide 143](images/lec5_p143.png)

### 幻灯片内容

Absolute positional embeddings
Idea. Add position-speciﬁc embedding to token vector
 = some terms +
What choice for position embeddings?
Figure adapted from Attention Is All You Need, Vaswani et al., 2017.

### 通俗解释

这页内容：Absolute positional embeddings Idea. Add position-speciﬁc embedding to token vec...

---

## Slide 144

![Slide 144](images/lec5_p144.png)

### 幻灯片内容

Hardcoded position embeddings
2i
2i+1
. . .
. . .
Position
Proposal. A mix of sines and cosines.
between 0 and 1

### 通俗解释

这页内容：Hardcoded position embeddings 2i 2i+1 . . . . . . Position Proposal. A mix of si...

---

## Slide 145

![Slide 145](images/lec5_p145.png)

### 幻灯片内容

Hardcoded position embeddings
2i
2i+1
. . .
. . .
Position
Proposal. A mix of sines and cosines.
greater than sequence 
lengths

### 通俗解释

这页内容：Hardcoded position embeddings 2i 2i+1 . . . . . . Position Proposal. A mix of si...

---

## Slide 146

![Slide 146](images/lec5_p146.png)

### 幻灯片内容

Hardcoded position embeddings
Figure from Transformer Architecture: The Positional Encoding, Kazemnejad, 2019.
Position embeddings values
Dimension depth
Sequence 
position
high frequency
low frequency

### 通俗解释

这页内容：Hardcoded position embeddings Figure from Transformer Architecture: The Position...

---

## Slide 147

![Slide 147](images/lec5_p147.png)

### 幻灯片内容

Hardcoded position embeddings
2i
2i+1
. . .
. . .
Position
with

### 通俗解释

这页内容：Hardcoded position embeddings 2i 2i+1 . . . . . . Position with...

---

## Slide 148

![Slide 148](images/lec5_p148.png)

### 幻灯片内容

Hardcoded position embeddings
2i
2i+1
. . .
. . .
Position
2i
2i+1
. . .
. . .
Position

### 通俗解释

这页内容：Hardcoded position embeddings 2i 2i+1 . . . . . . Position 2i 2i+1 . . . . . . P...

---

## Slide 149

![Slide 149](images/lec5_p149.png)

### 幻灯片内容

Hardcoded position embeddings
Property:

### 通俗解释

这页内容：Hardcoded position embeddings Property:...

---

## Slide 150

![Slide 150](images/lec5_p150.png)

### 幻灯片内容

Hardcoded position embeddings
~all cosines drop
high frequency terms 
cancel out
residual low 
frequency terms

### 通俗解释

这页内容：Hardcoded position embeddings ~all cosines drop high frequency terms  cancel out...

---

## Slide 151

![Slide 151](images/lec5_p151.png)

### 幻灯片内容

Discussion
Beneﬁts.
●
Simple to implement
●
Does the job well as a baseline
●
Gives every position a direct representational identity

### 通俗解释

这页内容：Discussion Beneﬁts. ● Simple to implement ● Does the job well as a baseline ● Gi...

---

## Slide 152

![Slide 152](images/lec5_p152.png)

### 幻灯片内容

Discussion
Beneﬁts.
●
Simple to implement
●
Does the job well as a baseline
●
Gives every position a direct representational identity
Limitations. 
●
Doesn't seem to be injected at the appropriate place
●
Side eﬀect: extra interaction terms
●
Position embedding also makes it to value embeddings

### 通俗解释

这页内容：Discussion Beneﬁts. ● Simple to implement ● Does the job well as a baseline ● Gi...

---

## Slide 153

![Slide 153](images/lec5_p153.png)

### 幻灯片内容

Absolute position embeddings
Who used it?
Figures adapted from Attention Is All You Need, Vaswani et al., 2017, An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale, 
Dosovitskiy et al., 2020, Scalable Diﬀusion Models with Transformers, Peebles et al., 2022.
Original Transformer
2017
Original ViT
2020
Original DiT
2022

### 通俗解释

这页内容：Absolute position embeddings Who used it? Figures adapted from Attention Is All ...

---

## Slide 154

![Slide 154](images/lec5_p154.png)

### 幻灯片内容

From absolute to relative position info
Reﬁnement. Any way to move position information to where it's intuitively needed?
Figure adapted from Attention Is All You Need, Vaswani et al., 2017.

### 通俗解释

这页内容：From absolute to relative position info Reﬁnement. Any way to move position info...

---

## Slide 155

![Slide 155](images/lec5_p155.png)

### 幻灯片内容

Default choice nowadays: rotations in attention layer
Idea. Rotate query and key vectors with rotation matrix
RoPE = Rotary Position Embeddings
RoFormer: Enhanced Transformer with Rotary Position Embeddings, Su et al., 2021.
Figure from Super Study Guide: Transformers & Large Language Models, Amidi et al., 2024.
queries
keys

### 通俗解释

这页内容：Default choice nowadays: rotations in attention layer Idea. Rotate query and key...

---

## Slide 156

![Slide 156](images/lec5_p156.png)

### 幻灯片内容

Default choice nowadays: rotations in attention layer
Beneﬁts. Relative distance nicely captured:
RoFormer: Enhanced Transformer with Rotary Position Embeddings, Su et al., 2021.
eﬀective rotation by angle

### 通俗解释

这页内容：Default choice nowadays: rotations in attention layer Beneﬁts. Relative distance...

---

## Slide 157

![Slide 157](images/lec5_p157.png)

### 幻灯片内容

Generalization to 2D?
Text.
1
2
3
4
5
6
...
✅

### 通俗解释

这页内容：Generalization to 2D? Text. 1 2 3 4 5 6 ... ✅...

---

## Slide 158

![Slide 158](images/lec5_p158.png)

### 幻灯片内容

1
2
3
4
5
6
7
8
9
Generalization to 2D?
Text.
1
Images.
2
3
4
5
6
...
✅
❓

### 通俗解释

这页内容：1 2 3 4 5 6 7 8 9 Generalization to 2D? Text. 1 Images. 2 3 4 5 6 ... ✅ ❓...

---

## Slide 159

![Slide 159](images/lec5_p159.png)

### 幻灯片内容

Generalization to 2D?
First idea. Axial RoPE
1D
2D
even indices
odd indices
Rotary Position Embedding for Vision Transformer, Heo et al., 2024.

### 通俗解释

这页内容：Generalization to 2D? First idea. Axial RoPE 1D 2D even indices odd indices Rota...

---

## Slide 160

![Slide 160](images/lec5_p160.png)

### 幻灯片内容

Generalization to 2D?
Problems. No cross axes interactions + segregated information is arbitrary
no interaction!
Rotary Position Embedding for Vision Transformer, Heo et al., 2024.

### 通俗解释

这页内容：Generalization to 2D? Problems. No cross axes interactions + segregated informat...

---

## Slide 161

![Slide 161](images/lec5_p161.png)

### 幻灯片内容

2D RoPE
Proposal. Mix both axes as part of the same rotation matrix
Rotary Position Embedding for Vision Transformer, Heo et al., 2024.

### 通俗解释

这页内容：2D RoPE Proposal. Mix both axes as part of the same rotation matrix Rotary Posit...

---

## Slide 162

![Slide 162](images/lec5_p162.png)

### 幻灯片内容

2D RoPE
Consequence. Avoid axes artifacts.
Figure from Rotary Position Embedding for Vision Transformer, Heo et al., 2024.
2D Axial RoPE
2D Mixed RoPE
Patch position

### 通俗解释

这页内容：2D RoPE Consequence. Avoid axes artifacts. Figure from Rotary Position Embedding...

---

## Slide 163

![Slide 163](images/lec5_p163.png)

### 幻灯片内容

Scaling RoPE
Common case. Resolution variations?
vs
0,0
2,0
0,2
0,0
0,5
5,0

### 通俗解释

这页内容：Scaling RoPE Common case. Resolution variations? vs 0,0 2,0 0,2 0,0 0,5 5,0...

---

## Slide 164

![Slide 164](images/lec5_p164.png)

### 幻灯片内容

0,0
2,0
0,2
0,0
0,5
5,0
Scaling RoPE
Problem. Spatial meaning also changes.
vs
"center"
"center"

### 通俗解释

这页内容：0,0 2,0 0,2 0,0 0,5 5,0 Scaling RoPE Problem. Spatial meaning also changes. vs "...

---

## Slide 165

![Slide 165](images/lec5_p165.png)

### 幻灯片内容

Scaling RoPE
Remedy. Scale to canonical coordinates.
vs
-1,-1
1,-1
-1,1
-3,-3
-3,2
2,-3
0,0
≈ 0,0
Seedream 2.0: A Native Chinese-English Bilingual Image Generation Foundation Model, Gong et al., 2025.

### 通俗解释

这页内容：Scaling RoPE Remedy. Scale to canonical coordinates. vs -1,-1 1,-1 -1,1 -3,-3 -3...

---

## Slide 166

![Slide 166](images/lec5_p166.png)

### 幻灯片内容

Multimodal RoPE
Qwen-Image Technical Report, Wu et al., 2025.
Potential area of interest
Common case. Multimodality?

### 通俗解释

这页内容：Multimodal RoPE Qwen-Image Technical Report, Wu et al., 2025. Potential area of ...

---

## Slide 167

![Slide 167](images/lec5_p167.png)

### 幻灯片内容

Multimodal RoPE
2D
1D
How to reconcile the two?

### 通俗解释

这页内容：Multimodal RoPE 2D 1D How to reconcile the two?...

---

## Slide 168

![Slide 168](images/lec5_p168.png)

### 幻灯片内容

Multimodal RoPE
Qwen-Image Technical Report, Wu et al., 2025.
...
MSRoPE = Multimodal Scalable RoPE
Beneﬁts.
●
Image and text can cohabit without 
interference

### 通俗解释

这页内容：Multimodal RoPE Qwen-Image Technical Report, Wu et al., 2025. ... MSRoPE = Multi...

---

## Slide 169

![Slide 169](images/lec5_p169.png)

### 幻灯片内容

Multimodal RoPE
Qwen-Image Technical Report, Wu et al., 2025.
...
MSRoPE = Multimodal Scalable RoPE
Beneﬁts.
●
Image and text can cohabit without 
interference  
●
Text is functionally equivalent to 1D 
RoPE

### 通俗解释

这页内容：Multimodal RoPE Qwen-Image Technical Report, Wu et al., 2025. ... MSRoPE = Multi...

---

## Slide 170

![Slide 170](images/lec5_p170.png)

### 幻灯片内容

Conclusion
Embedding positions = open problem.
●
Many variations out there
●
Dust hasn't settled yet
●
Trade-oﬀs

### 通俗解释

这页内容：Conclusion Embedding positions = open problem. ● Many variations out there ● Dus...

---

## Slide 171

![Slide 171](images/lec5_p171.png)

### 通俗解释

过渡页或标题页。

---
