# Stanford CME 296 - Lecture 4: Latent Space & Guidance (VAE, CLIP, CFG)

> **课程**: Stanford CME 296 - Diffusion & Large Vision Models
> **讲师**: Afshine Amidi & Shervine Amidi
> **视频**: [YouTube 1:40:58](https://www.youtube.com/watch?v=WUUq6TVAu8U&list=PLoROMvodv4rNdy8rt2rZ4T2xM0OjADnfu&index=4)
> **Slides PDF**: [spring26-cme296-lecture4.pdf](../spring26-cme296-lecture4.pdf)
> **总页数**: 148 页幻灯片

---

## Slide 1

![Slide 1](images/lec4_p001.png)

### 📝 幻灯片内容

CME 296: Diﬀusion &
Large Vision Models
Afshine Amidi & Shervine Amidi
Lecture 4

### 💡 通俗解释

*（待补充解释）*

---

## Slide 2

![Slide 2](images/lec4_p002.png)

### 📝 幻灯片内容

Recap of last episodes…
Lecture 1: 
Diﬀusion, 
DDPM

### 💡 通俗解释

*（待补充解释）*

---

## Slide 3

![Slide 3](images/lec4_p003.png)

### 📝 幻灯片内容

Recap of last episodes…
Lecture 2: 
Score matching, 
SDE
Lecture 1: 
Diﬀusion, 
DDPM

### 💡 通俗解释

*（待补充解释）*

---

## Slide 4

![Slide 4](images/lec4_p004.png)

### 📝 幻灯片内容

Recap of last episodes…
Lecture 3:
Flow matching
Lecture 2: 
Score matching, 
SDE
Lecture 1: 
Diﬀusion, 
DDPM

### 💡 通俗解释

*（待补充解释）*

---

## Slide 5

![Slide 5](images/lec4_p005.png)

### 📝 幻灯片内容

Recap of last episodes…
Lecture 3:
Flow matching
Lecture 2: 
Score matching, 
SDE
Lecture 1: 
Diﬀusion, 
DDPM

### 💡 通俗解释

*（待补充解释）*

---

## Slide 6

![Slide 6](images/lec4_p006.png)

### 📝 幻灯片内容

Recap of last episodes…
Lecture 3:
Flow matching
Lecture 2: 
Score matching, 
SDE
Lecture 1: 
Diﬀusion, 
DDPM

### 💡 通俗解释

*（待补充解释）*

---

## Slide 7

![Slide 7](images/lec4_p007.png)

### 📝 幻灯片内容

Recap of last episodes…
Lecture 3:
Flow matching
Lecture 2: 
Score matching, 
SDE
Lecture 1: 
Diﬀusion, 
DDPM

### 💡 通俗解释

*（待补充解释）*

---

## Slide 8

![Slide 8](images/lec4_p008.png)

### 📝 幻灯片内容

Today's lecture
A teddy bear 
reading a book
Condition
Black box 
architecture
Today's lecture: Multimodal guided generation
Representation
Guided generation

### 💡 通俗解释

*（待补充解释）*

---

## Slide 9

![Slide 9](images/lec4_p009.png)

### 📝 幻灯片内容

Today's lecture: Part 1
A teddy bear 
reading a book
Condition
Black box 
architecture
Today's lecture: Multimodal guided generation
Representation
1
Guided generation

### 💡 通俗解释

*（待补充解释）*

---

## Slide 10

![Slide 10](images/lec4_p010.png)

### 📝 幻灯片内容

From pixel to latent space
Latent diﬀusion models
Text representation
Image representation
Contrastive learning
Guidance
Diﬀusion & 
Large Vision 
Models

### 💡 通俗解释

*（待补充解释）*

---

## Slide 11

![Slide 11](images/lec4_p011.png)

### 📝 幻灯片内容

Pixel space
Naive approach. Represent everything in pixel space
R
G
B
Number of pixels

### 💡 通俗解释

*（待补充解释）*

---

## Slide 12

![Slide 12](images/lec4_p012.png)

### 📝 幻灯片内容

Limitations of the pixel space
●
High dimensionality

### 💡 通俗解释

*（待补充解释）*

---

## Slide 13

![Slide 13](images/lec4_p013.png)

### 📝 幻灯片内容

Limitations of the pixel space
●
High dimensionality
●
Redundant information (correlated pixels)

### 💡 通俗解释

*（待补充解释）*

---

## Slide 14

![Slide 14](images/lec4_p014.png)

### 📝 幻灯片内容

Limitations of the pixel space
●
High dimensionality
●
Redundant information (correlated pixels)
●
Representation not meaningful (if we move in space, image becomes 
gibberish)

### 💡 通俗解释

*（待补充解释）*

---

## Slide 15

![Slide 15](images/lec4_p015.png)

### 📝 幻灯片内容

Limitations of the pixel space
●
High dimensionality
●
Redundant information (correlated pixels)
●
Representation not meaningful (if we move in space, image becomes 
gibberish)
👍
👎

### 💡 通俗解释

*（待补充解释）*

---

## Slide 16

![Slide 16](images/lec4_p016.png)

### 📝 幻灯片内容

Wish list of an ideal space
Tractable dimension
●
High dimensionality
●
Redundant information (correlated pixels)
●
Representation not meaningful (if we move in space, image becomes 
gibberish)

### 💡 通俗解释

*（待补充解释）*

---

## Slide 17

![Slide 17](images/lec4_p017.png)

### 📝 幻灯片内容

Wish list of an ideal space
Tractable dimension
●
High dimensionality
●
Redundant information (correlated pixels)
Compact representation
●
Representation not meaningful (if we move in space, image becomes 
gibberish)

### 💡 通俗解释

*（待补充解释）*

---

## Slide 18

![Slide 18](images/lec4_p018.png)

### 📝 幻灯片内容

Wish list of an ideal space
Tractable dimension
●
High dimensionality
●
Redundant information (correlated pixels)
●
Representation not meaningful (if we move in space, image becomes 
gibberish)
Compact representation
Meaningful representation

### 💡 通俗解释

*（待补充解释）*

---

## Slide 19

![Slide 19](images/lec4_p019.png)

### 📝 幻灯片内容

Terminology
Semantic similarity
●
Structural
●
Global geometry
●
"Low" frequency

### 💡 通俗解释

*（待补充解释）*

---

## Slide 20

![Slide 20](images/lec4_p020.png)

### 📝 幻灯片内容

Terminology
Semantic similarity
Perceptual similarity
●
Structural
●
Global geometry
●
"Low" frequency
●
Local
●
Texture
●
"High" frequency

### 💡 通俗解释

*（待补充解释）*

---

## Slide 21

![Slide 21](images/lec4_p021.png)

### 📝 幻灯片内容

Attempt 1: Learn representation via an autoencoder
Encoder
Decoder
Bottleneck
Pixel space
Pixel space
Latent space
Stacked Convolutional Auto-Encoders for Hierarchical Feature Extraction, Masci et al., 2011.
Goal. Learn latent representation via "proxy task" (reconstruction)
Autoencoder

### 💡 通俗解释

*（待补充解释）*

---

## Slide 22

![Slide 22](images/lec4_p022.png)

### 📝 幻灯片内容

Attempt 1: Learn representation via an autoencoder
Pixel space
Pixel space
Latent space
Goal. Learn latent representation via "proxy task" (reconstruction)
Spatial compression ratio

### 💡 通俗解释

*（待补充解释）*

---

## Slide 23

![Slide 23](images/lec4_p023.png)

### 📝 幻灯片内容

Encoder
Downsampling operations via convolutions
Encoder
Pixel space
Latent space

### 💡 通俗解释

*（待补充解释）*

---

## Slide 24

![Slide 24](images/lec4_p024.png)

### 📝 幻灯片内容

Quick refresher on convolutions
Convolution
VIP cheatsheets on Convolutional Neural Networks, Amidi, 2018.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 25

![Slide 25](images/lec4_p025.png)

### 📝 幻灯片内容

Quick refresher on convolutions
Convolution
Pooling
VIP cheatsheets on Convolutional Neural Networks, Amidi, 2018.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 26

![Slide 26](images/lec4_p026.png)

### 📝 幻灯片内容

Decoder
Latent space
Decoder
Pixel space
Upsampling operations via reverse convolutions

### 💡 通俗解释

*（待补充解释）*

---

## Slide 27

![Slide 27](images/lec4_p027.png)

### 📝 幻灯片内容

Loss function of autoencoder
Loss. Compare input
Goal. Learn how to reconstruct input 
with reconstructed input
AE = AutoEncoder

### 💡 通俗解释

*（待补充解释）*

---

## Slide 28

![Slide 28](images/lec4_p028.png)

### 📝 幻灯片内容

Checklist for attempt 1
✅
✅
Tractable dimension
Compact representation
❌
Meaningful representation

### 💡 通俗解释

*（待补充解释）*

---

## Slide 29

![Slide 29](images/lec4_p029.png)

### 📝 幻灯片内容

Attempt 2: Learn a constrained latent space
Auto-Encoding Variational Bayes, Kingma et al., 2013.
Goal. Enforce some "structure" on the latent space
Encoder
Decoder
Constrained 
bottleneck
Pixel space
Pixel space
Latent space
Constrained 
Autoencoder

### 💡 通俗解释

*（待补充解释）*

---

## Slide 30

![Slide 30](images/lec4_p030.png)

### 📝 幻灯片内容

Attempt 2: Learn a constrained latent space
Goal. Enforce some "structure" on the latent space
Encoder
Decoder
Pixel space
Pixel space
Latent space
Constrained 
Autoencoder
Constrained 
bottleneck

### 💡 通俗解释

*（待补充解释）*

---

## Slide 31

![Slide 31](images/lec4_p031.png)

### 📝 幻灯片内容

Revised encoder
Encoder
Pixel space
Latent space

### 💡 通俗解释

*（待补充解释）*

---

## Slide 32

![Slide 32](images/lec4_p032.png)

### 📝 幻灯片内容

Revised decoder
Latent space
Decoder
Pixel space

### 💡 通俗解释

*（待补充解释）*

---

## Slide 33

![Slide 33](images/lec4_p033.png)

### 📝 幻灯片内容

Revised decoder
Latent space
Decoder
Pixel space
Assumption: constant variance (for simplicity)

### 💡 通俗解释

*（待补充解释）*

---

## Slide 34

![Slide 34](images/lec4_p034.png)

### 💡 通俗解释

*（待补充解释）*

---

## Slide 35

![Slide 35](images/lec4_p035.png)

### 📝 幻灯片内容

Step 1: Re-using ELBO trick from Lecture 1!
Derive lower bound for maximum (log-)likelihood estimation
1
ELBO = Evidence Lower BOund
Derivation: Use Jensen's inequality on a convenient variational distribution

### 💡 通俗解释

*（待补充解释）*

---

## Slide 36

![Slide 36](images/lec4_p036.png)

### 📝 幻灯片内容

Step 2: Expand terms of the lower bound
Expand terms of lower bound
2
Derivation: Use properties of the log function and rearrange terms

### 💡 通俗解释

*（待补充解释）*

---

## Slide 37

![Slide 37](images/lec4_p037.png)

### 📝 幻灯片内容

Loss function of variational autoencoder
Goal. Learn how to reconstruct input using a structured latent space
Loss. Trade-oﬀ between reconstruction and latent space structure:
Reconstruction
Regularization of 
latent space
VAE = Variational AutoEncoder
Auto-Encoding Variational Bayes, Kingma et al., 2013.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 38

![Slide 38](images/lec4_p038.png)

### 📝 幻灯片内容

Checklist for attempt 2
✅
✅
Tractable dimension
Compact representation
✅
Meaningful representation
❌
Truthful representation

### 💡 通俗解释

*（待补充解释）*

---

## Slide 39

![Slide 39](images/lec4_p039.png)

### 📝 幻灯片内容

Attempt 3: address limitations of original VAE
Reconstruction
Latent space 
regularization
Goal. Avoid blurriness!

### 💡 通俗解释

*（待补充解释）*

---

## Slide 40

![Slide 40](images/lec4_p040.png)

### 📝 幻灯片内容

Refresher on reconstruction loss
Idea. Check reconstruction of input
Description. 
or 
      pixel-wise distance between output and actual
Weight.
If 
too high, this can produce blurry outputs

### 💡 通俗解释

*（待补充解释）*

---

## Slide 41

![Slide 41](images/lec4_p041.png)

### 📝 幻灯片内容

Refresher on KL regularization
Idea. Make latent space more structured
Description. KL divergence between the output of the encoder and the prior
Weight.
If 
too high, this can lead to "posterior collapse"

### 💡 通俗解释

*（待补充解释）*

---

## Slide 42

![Slide 42](images/lec4_p042.png)

### 📝 幻灯片内容

Combat blurriness with perceptual loss

### 💡 通俗解释

*（待补充解释）*

---

## Slide 43

![Slide 43](images/lec4_p043.png)

### 📝 幻灯片内容

Combat blurriness with perceptual loss
 Illustration from Visualizing and Understanding Convolutional Networks, Zeiler et al., 2013.
Example of feature 
maps in early layers

### 💡 通俗解释

*（待补充解释）*

---

## Slide 44

![Slide 44](images/lec4_p044.png)

### 📝 幻灯片内容

Combat blurriness with perceptual loss
Idea. Force model to pay attention to shapes sensitive to human eye (edges, 
shapes) and have some translation invariance

### 💡 通俗解释

*（待补充解释）*

---

## Slide 45

![Slide 45](images/lec4_p045.png)

### 📝 幻灯片内容

Combat blurriness with perceptual loss
Idea. Force model to pay attention to shapes sensitive to human eye (edges, 
shapes) and have some translation invariance
Description. Learned Perceptual Image Patch Similarity (LPIPS)
The Unreasonable Eﬀectiveness of Deep Features as a Perceptual Metric, Zhang et al., 2018.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 46

![Slide 46](images/lec4_p046.png)

### 📝 幻灯片内容

Combat blurriness with perceptual loss
Idea. Force model to pay attention to shapes sensitive to human eye (edges, 
shapes) and have some translation invariance
Description. Learned Perceptual Image Patch Similarity (LPIPS)
The Unreasonable Eﬀectiveness of Deep Features as a Perceptual Metric, Zhang et al., 2018.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 47

![Slide 47](images/lec4_p047.png)

### 📝 幻灯片内容

Combat blurriness with perceptual loss
Idea. Force model to pay attention to shapes sensitive to human eye (edges, 
shapes) and have some translation invariance
Description. Learned Perceptual Image Patch Similarity (LPIPS)
Weight.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 48

![Slide 48](images/lec4_p048.png)

### 📝 幻灯片内容

No
"checkerboard artifact"
Combat blurriness with perceptual loss
If 
too high, this can produce "checkerboard artifacts"
Illustrations from Deconvolution and Checkerboard Artifacts, Odena et al., 2016.
Presence of  
"checkerboard artifact"

### 💡 通俗解释

*（待补充解释）*

---

## Slide 49

![Slide 49](images/lec4_p049.png)

### 📝 幻灯片内容

Make output more realistic with adversarial loss
Decoder
Discriminator
Real or fake?

### 💡 通俗解释

*（待补充解释）*

---

## Slide 50

![Slide 50](images/lec4_p050.png)

### 📝 幻灯片内容

Make output more realistic with adversarial loss
Decoder
Discriminator
Real or fake?

### 💡 通俗解释

*（待补充解释）*

---

## Slide 51

![Slide 51](images/lec4_p051.png)

### 📝 幻灯片内容

Make output more realistic with adversarial loss
Idea. Prevent blurriness by being force to produce a realistic image
Description. Incentivize discriminator (critic) to be fooled
Weight.
If 
too high, this may lead to "mode collapse" and ignore the latent

### 💡 通俗解释

*（待补充解释）*

---

## Slide 52

![Slide 52](images/lec4_p052.png)

### 📝 幻灯片内容

Summary of reﬁned VAE
Reconstruction
Adversarial
Perception
Mitigate 
blurriness
Latent space regularization

### 💡 通俗解释

*（待补充解释）*

---

## Slide 53

![Slide 53](images/lec4_p053.png)

### 📝 幻灯片内容

From pixel to latent space
Latent diﬀusion models
Text representation
Image representation
Contrastive learning
Guidance
Diﬀusion & 
Large Vision 
Models

### 💡 通俗解释

*（待补充解释）*

---

## Slide 54

![Slide 54](images/lec4_p054.png)

### 📝 幻灯片内容

Diﬀusion in latent space
Train VAE
Train image generation model in VAE latent space using frozen 
VAE encoder
1
2
Training.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 55

![Slide 55](images/lec4_p055.png)

### 📝 幻灯片内容

Training leverages encoder
Pixel space
Encoder
Latent space
Latent space

### 💡 通俗解释

*（待补充解释）*

---

## Slide 56

![Slide 56](images/lec4_p056.png)

### 📝 幻灯片内容

Training leverages encoder
Pixel space
Encoder
Latent space
Latent space

### 💡 通俗解释

*（待补充解释）*

---

## Slide 57

![Slide 57](images/lec4_p057.png)

### 📝 幻灯片内容

Diﬀusion in latent space
Train VAE
Train image generation model in VAE latent space using frozen 
VAE encoder
1
2
Training.
Start from a noisy latent and perform diﬀusion / score matching / 
ﬂow matching in latent space
1
Inference.
Use VAE decoder to obtain ﬁnal image in pixel space
2

### 💡 通俗解释

*（待补充解释）*

---

## Slide 58

![Slide 58](images/lec4_p058.png)

### 📝 幻灯片内容

Inference leverages decoder
Latent space
Decoder
Pixel space

### 💡 通俗解释

*（待补充解释）*

---

## Slide 59

![Slide 59](images/lec4_p059.png)

### 📝 幻灯片内容

VAE used for image generation models
High-Resolution Image Synthesis with Latent Diﬀusion Models, Rombach et al., 2021.
●
Encoder: acts as a "low-pass ﬁlter"
Interesting experiment results in FLUX.2: Analyzing and Enhancing the Latent Space of FLUX – Representation Comparison, 2025.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 60

![Slide 60](images/lec4_p060.png)

### 📝 幻灯片内容

VAE used for image generation models
High-Resolution Image Synthesis with Latent Diﬀusion Models, Rombach et al., 2021.
●
Encoder: acts as a "low-pass ﬁlter"
●
Decoder: 
○
Responsible to convey low-level details via "texture hallucination"
○
Takes in a highly compressed low-dimensional vector and needs to 
convert it to a high-dimensional one
Interesting experiment results in FLUX.2: Analyzing and Enhancing the Latent Space of FLUX – Representation Comparison, 2025.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 61

![Slide 61](images/lec4_p061.png)

### 📝 幻灯片内容

VAE used for image generation models
●
Decoder is 2x bigger than Encoder
High-Resolution Image Synthesis with Latent Diﬀusion Models, Rombach et al., 2021.
●
Encoder: acts as a "low-pass ﬁlter"
●
Decoder: 
○
Responsible to convey low-level details via "texture hallucination"
○
Takes in a highly compressed low-dimensional vector and needs to 
convert it to a high-dimensional one
Interesting experiment results in FLUX.2: Analyzing and Enhancing the Latent Space of FLUX – Representation Comparison, 2025.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 62

![Slide 62](images/lec4_p062.png)

### 📝 幻灯片内容

From pixel to latent space
Latent diﬀusion models
Text representation
Image representation
Contrastive learning
Guidance
Diﬀusion & 
Large Vision 
Models

### 💡 通俗解释

*（待补充解释）*

---

## Slide 63

![Slide 63](images/lec4_p063.png)

### 📝 幻灯片内容

Today's lecture: Part 2
A teddy bear 
reading a book
Condition
Black box 
architecture
Today's lecture: Multimodal guided generation
Representation
1
2
Guided generation

### 💡 通俗解释

*（待补充解释）*

---

## Slide 64

![Slide 64](images/lec4_p064.png)

### 📝 幻灯片内容

Class of models
Recurrent neural networks (RNNs)
Long short-term memory (LSTM)
Word2vec
Transformers
Large Language Models
1980s
1997
2013
2017
2020s

### 💡 通俗解释

*（待补充解释）*

---

## Slide 65

![Slide 65](images/lec4_p065.png)

### 📝 幻灯片内容

Tokenization
A cute teddy bear is reading.
A
cute
teddy bear
is
reading
.
A
cute
teddy
is
reading
.
bear
A
c
u
t
e
t
e
d
d
y
b
e
a
r
i
s
r
e
a
d
i
n
g
.
_
_
_
_
_
A
cute
ted
is
read
.
bear
##dy
##ing
sub-word
word
arbitrary
character

### 💡 通俗解释

*（待补充解释）*

---

## Slide 66

![Slide 66](images/lec4_p066.png)

### 📝 幻灯片内容

Transformer architecture
Attention Is All You Need, Vaswani et al., 2017.
●
Introduced in 2017 for machine translation
●
Relies on the concept of attention
●
Concepts of query, key, value
●
Proxy task: next token prediction
●
Weaker inductive biases
●
More generalizability
Context
Beneﬁts

### 💡 通俗解释

*（待补充解释）*

---

## Slide 67

![Slide 67](images/lec4_p067.png)

### 📝 幻灯片内容

Attention mechanism 
Concept of Query, Key, Value
"Super Study Guide: Transformers & Large Language Models", by Amidi, 2024.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 68

![Slide 68](images/lec4_p068.png)

### 📝 幻灯片内容

Attention mechanism
Eﬃcient computations with matrices:
Figure adapted from “Attention Is All You Need”, Vaswani et al., 2017.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 69

![Slide 69](images/lec4_p069.png)

### 📝 幻灯片内容

Attention locations
Self-attention
●
Encoder-Encoder
●
Decoder-Decoder
Cross-attention
●
Encoder-Decoder
Figure adapted from “Attention Is All You Need”, Vaswani et al., 2017.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 70

![Slide 70](images/lec4_p070.png)

### 📝 幻灯片内容

Input
Overview
●
Text is "tokenized"
●
Learned embeddings for tokens
Parameters
●
V: vocabulary size
●
d_model: embedding dimensions
Figure adapted from “Attention Is All You Need”, Vaswani et al., 2017.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 71

![Slide 71](images/lec4_p071.png)

### 📝 幻灯片内容

... with a trick!
Positional encoding
Idea:
●
Add position information to inputs
●
Can be either learned or hardcoded
Goal: let model understand relative input position
Left ﬁgure adapted from “Attention Is All You Need”, Vaswani et al., 2017.
Right ﬁgures adapted from “Transformer Architecture: The Positional Encoding”, Kazemnejad, 2019.
+1
-1
Dimension
Position
Position
Position
max
dot product
min

### 💡 通俗解释

*（待补充解释）*

---

## Slide 72

![Slide 72](images/lec4_p072.png)

### 📝 幻灯片内容

Encoder
Overview
●
Encoder-Encoder self-attention
●
Feed Forward Neural Network
●
Normalization layer
Parameters
●
N: layers stacked
●
h: number of attention heads
●
d_FF, d_key, d_value: sub-layer dimension 
●
d_model: embedding dimensions
Figure adapted from “Attention Is All You Need”, Vaswani et al., 2017.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 73

![Slide 73](images/lec4_p073.png)

### 📝 幻灯片内容

Output "shifted right"
Overview
●
Learned embeddings for output tokens
●
In practice, will start with [BOS]
Parameters
●
V: vocabulary size
●
d_model: embedding dimensions
Figure adapted from “Attention Is All You Need”, Vaswani et al., 2017.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 74

![Slide 74](images/lec4_p074.png)

### 📝 幻灯片内容

Decoder
Overview
●
Decoder-Decoder self-attention
●
Encoder-Decoder cross-attention
●
Feed Forward Neural Network
●
Normalization layer
Parameters
●
N: layers stacked
●
h: number of attention heads
●
d_FF, d_key, d_value: sub-layer dimension 
●
d_model: embedding dimensions
Figure adapted from “Attention Is All You Need”, Vaswani et al., 2017.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 75

![Slide 75](images/lec4_p075.png)

### 📝 幻灯片内容

Output
Overview
●
Linear projection
●
Classiﬁcation problem that outputs 
probability of belonging to a class, where 
class = word
Parameters
●
V: vocabulary size
●
d_model: embedding dimensions
Figure adapted from “Attention Is All You Need”, Vaswani et al., 2017.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 76

![Slide 76](images/lec4_p076.png)

### 📝 幻灯片内容

Typical embeddings location
Figure adapted from “Attention Is All You Need”, Vaswani et al., 2017.
last hidden state of the encoder

### 💡 通俗解释

*（待补充解释）*

---

## Slide 77

![Slide 77](images/lec4_p077.png)

### 📝 幻灯片内容

From pixel to latent space
Latent diﬀusion models
Text representation
Image representation
Contrastive learning
Guidance
Diﬀusion & 
Large Vision 
Models

### 💡 通俗解释

*（待补充解释）*

---

## Slide 78

![Slide 78](images/lec4_p078.png)

### 📝 幻灯片内容

Today's lecture: Part 2
Condition
Black box 
architecture
Today's lecture: Multimodal guided generation
Representation
1
2
Guided generation

### 💡 通俗解释

*（待补充解释）*

---

## Slide 79

![Slide 79](images/lec4_p079.png)

### 📝 幻灯片内容

Adapting attention mechanism to images
It's just numbers...
Figure adapted from "Super Study Guide: Transformers & Large Language Models", by Amidi, 2024.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 80

![Slide 80](images/lec4_p080.png)

### 📝 幻灯片内容

Adapting attention mechanism to images
It's just numbers...

### 💡 通俗解释

*（待补充解释）*

---

## Slide 81

![Slide 81](images/lec4_p081.png)

### 📝 幻灯片内容

Adapting attention mechanism to images
...that could well represent images!

### 💡 通俗解释

*（待补充解释）*

---

## Slide 82

![Slide 82](images/lec4_p082.png)

### 📝 幻灯片内容

Vision Transformer
An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale, Dosovitskiy et al., 2020.
ViT = Vision Transformer

### 💡 通俗解释

*（待补充解释）*

---

## Slide 83

![Slide 83](images/lec4_p083.png)

### 💡 通俗解释

*（待补充解释）*

---

## Slide 84

![Slide 84](images/lec4_p084.png)

### 📝 幻灯片内容

ViT end-to-end example
P
P
C
Linear
D

### 💡 通俗解释

*（待补充解释）*

---

## Slide 85

![Slide 85](images/lec4_p085.png)

### 💡 通俗解释

*（待补充解释）*

---

## Slide 86

![Slide 86](images/lec4_p086.png)

### 💡 通俗解释

*（待补充解释）*

---

## Slide 87

![Slide 87](images/lec4_p087.png)

### 📝 幻灯片内容

[CLS]
embedding
ViT end-to-end example

### 💡 通俗解释

*（待补充解释）*

---

## Slide 88

![Slide 88](images/lec4_p088.png)

### 📝 幻灯片内容

[CLS]
embedding
position embedding
ViT end-to-end example

### 💡 通俗解释

*（待补充解释）*

---

## Slide 89

![Slide 89](images/lec4_p089.png)

### 📝 幻灯片内容

[CLS]
position-aware embedding
ViT end-to-end example

### 💡 通俗解释

*（待补充解释）*

---

## Slide 90

![Slide 90](images/lec4_p090.png)

### 💡 通俗解释

*（待补充解释）*

---

## Slide 91

![Slide 91](images/lec4_p091.png)

### 📝 幻灯片内容

[CLS]
ENCODER
ViT architecture
ViT end-to-end example

### 💡 通俗解释

*（待补充解释）*

---

## Slide 92

![Slide 92](images/lec4_p092.png)

### 📝 幻灯片内容

[CLS]
ENCODER
ViT architecture
encoded embeddings
ViT end-to-end example

### 💡 通俗解释

*（待补充解释）*

---

## Slide 93

![Slide 93](images/lec4_p093.png)

### 📝 幻灯片内容

[CLS]
ENCODER
ViT architecture
FFN
Class
teddy bear
ViT end-to-end example

### 💡 通俗解释

*（待补充解释）*

---

## Slide 94

![Slide 94](images/lec4_p094.png)

### 📝 幻灯片内容

Discussion
Limitations.
●
Supervised ViT good but needs labels
●
Fits to narrow category-level representation that has to be speciﬁed in 
advance

### 💡 通俗解释

*（待补充解释）*

---

## Slide 95

![Slide 95](images/lec4_p095.png)

### 📝 幻灯片内容

Discussion
Limitations.
●
Supervised ViT good but needs labels
●
Fits to narrow category-level representation that has to be speciﬁed in 
advance
Other approaches.
●
We didn’t have that problem for text because tasks that work are already 
self-supervised
●
Popular work: self-DIstillation with NO labels
Emerging Properties in Self-Supervised Vision Transformers, Caron et al., 2021.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 96

![Slide 96](images/lec4_p096.png)

### 📝 幻灯片内容

Discussion
How to make image and text 
embeddings comparable?

### 💡 通俗解释

*（待补充解释）*

---

## Slide 97

![Slide 97](images/lec4_p097.png)

### 📝 幻灯片内容

From pixel to latent space
Latent diﬀusion models
Text representation
Image representation
Contrastive learning
Guidance
Diﬀusion & 
Large Vision 
Models

### 💡 通俗解释

*（待补充解释）*

---

## Slide 98

![Slide 98](images/lec4_p098.png)

### 📝 幻灯片内容

Contrastive learning
Motivation. How to learn general image/text relationships?

### 💡 通俗解释

*（待补充解释）*

---

## Slide 99

![Slide 99](images/lec4_p099.png)

### 📝 幻灯片内容

Contrastive learning
Motivation. How to learn general image/text relationships?
Idea. Contrastive learning:
●
Group similar items together
●
Push away dissimilar items

### 💡 通俗解释

*（待补充解释）*

---

## Slide 100

![Slide 100](images/lec4_p100.png)

### 📝 幻灯片内容

Contrastive learning
teddy bear
water polo ball
close

### 💡 通俗解释

*（待补充解释）*

---

## Slide 101

![Slide 101](images/lec4_p101.png)

### 📝 幻灯片内容

Contrastive learning
teddy bear
water polo ball
far

### 💡 通俗解释

*（待补充解释）*

---

## Slide 102

![Slide 102](images/lec4_p102.png)

### 📝 幻灯片内容

Contrastive learning
teddy bear
water polo ball
far
far
close
close

### 💡 通俗解释

*（待补充解释）*

---

## Slide 103

![Slide 103](images/lec4_p103.png)

### 📝 幻灯片内容

Contrastive learning
low
similarity
high 
similarity
high 
similarity
low
similarity
teddy bear
water polo ball

### 💡 通俗解释

*（待补充解释）*

---

## Slide 104

![Slide 104](images/lec4_p104.png)

### 📝 幻灯片内容

How to ﬁnd a same space?
ENCODER
ViT architecture
[CLS]
Projection
u

### 💡 通俗解释

*（待补充解释）*

---

## Slide 105

![Slide 105](images/lec4_p105.png)

### 📝 幻灯片内容

How to ﬁnd a same space?
DECODER
"Vanilla" decoder-only architecture
[SOS]
[teddy]
[bear]
[EOS]
Projection
v teddy bear

### 💡 通俗解释

*（待补充解释）*

---

## Slide 106

![Slide 106](images/lec4_p106.png)

### 📝 幻灯片内容

Notation.
●
Similarity:
Loss formulation?
s �� 
,text
uT
�� text
v
u �� 
text
v
=

### 💡 通俗解释

*（待补充解释）*

---

## Slide 107

![Slide 107](images/lec4_p107.png)

### 📝 幻灯片内容

Notation.
●
Similarity:
●
Probability that image "       " matches text "teddy bear": 
Loss formulation?
s �� 
,text
uT
�� text
v
u �� 
text
v
p
teddy bear
=
=
exp( s
,teddy bear )
+
exp( s
,teddy bear )
exp( s
,water polo ball)

### 💡 通俗解释

*（待补充解释）*

---

## Slide 108

![Slide 108](images/lec4_p108.png)

### 📝 幻灯片内容

Contrastive learning
teddy bear
water polo ball

### 💡 通俗解释

*（待补充解释）*

---

## Slide 109

![Slide 109](images/lec4_p109.png)

### 📝 幻灯片内容

Notation.
●
Similarity:
●
Probability that image "       " matches text "teddy bear": 
●
Probability that text "teddy bear" matches image "     ":
Loss formulation?
s �� 
,text
uT
�� text
v
u �� 
text
v
p teddy bear
=
=
exp( s
,teddy bear )
+
exp( s
,teddy bear )
exp( s
,teddy bear )

### 💡 通俗解释

*（待补充解释）*

---

## Slide 110

![Slide 110](images/lec4_p110.png)

### 📝 幻灯片内容

Contrastive learning
teddy bear
water polo ball

### 💡 通俗解释

*（待补充解释）*

---

## Slide 111

![Slide 111](images/lec4_p111.png)

### 📝 幻灯片内容

1
2
water polo ball
Each term.
Loss formulation
L��   text=
log 
1
2
p
teddy bear
log p
water polo ball
(
)
+
L
�� 
  text
=
log pteddy bear
log p
(
)
+

### 💡 通俗解释

*（待补充解释）*

---

## Slide 112

![Slide 112](images/lec4_p112.png)

### 📝 幻灯片内容

1
2
water polo ball
Each term.
Total loss.
Loss formulation
L��   text=
log 
1
2
p
teddy bear
log p
water polo ball
(
)
+
L
�� 
  text
=
log pteddy bear
log p
(
)
+
L
1
2
=
( L��   text
+
L
�� 
  text
)

### 💡 通俗解释

*（待补充解释）*

---

## Slide 113

![Slide 113](images/lec4_p113.png)

### 📝 幻灯片内容

CLIP
CLIP = Contrastive Language-Image Pretraining

### 💡 通俗解释

*（待补充解释）*

---

## Slide 114

![Slide 114](images/lec4_p114.png)

### 📝 幻灯片内容

CLIP
CLIP = Contrastive Language-Image Pretraining

### 💡 通俗解释

*（待补充解释）*

---

## Slide 115

![Slide 115](images/lec4_p115.png)

### 📝 幻灯片内容

CLIP
CLIP = Contrastive Language-Image Pretraining

### 💡 通俗解释

*（待补充解释）*

---

## Slide 116

![Slide 116](images/lec4_p116.png)

### 📝 幻灯片内容

CLIP
CLIP = Contrastive Language-Image Pretraining
Learning Transferable Visual Models From Natural Language Supervision, Radford et al., 2021

### 💡 通俗解释

*（待补充解释）*

---

## Slide 117

![Slide 117](images/lec4_p117.png)

### 📝 幻灯片内容

Each term.
CLIP loss
1
N
L��   text=
log 
1
N
p
teddy bear
(
)
+
L
�� 
  text
=
log pteddy bear
...
(
)
+
...

### 💡 通俗解释

*（待补充解释）*

---

## Slide 118

![Slide 118](images/lec4_p118.png)

### 📝 幻灯片内容

Each term.
Total loss.
CLIP loss
1
N
L��   text=
log 
1
N
p
teddy bear
(
)
+
L
�� 
  text
=
log pteddy bear
...
(
)
+
L
1
2
=
( L��   text
+
L
�� 
  text
)
...

### 💡 通俗解释

*（待补充解释）*

---

## Slide 119

![Slide 119](images/lec4_p119.png)

### 📝 幻灯片内容

CLIP characteristics
Training.
●
Dataset: 400M of (image, caption) pairs
●
Visual encoder: ViT or CNN
●
Text encoder: Transformer-based
●
Loss works because of the assumption of "in-batch negatives"
Learning Transferable Visual Models From Natural Language Supervision, Radford et al., 2021

### 💡 通俗解释

*（待补充解释）*

---

## Slide 120

![Slide 120](images/lec4_p120.png)

### 📝 幻灯片内容

Training.
●
Dataset: 400M of (image, caption) pairs
●
Visual encoder: ViT or CNN
●
Text encoder: Transformer-based
●
Loss works because of the assumption of "in-batch negatives"
Results.
●
Reaches ~76% on ImageNet with no supervised training
●
Arguable possible leak from supervised sets, but still remarkable
Learning Transferable Visual Models From Natural Language Supervision, Radford et al., 2021
CLIP characteristics

### 💡 通俗解释

*（待补充解释）*

---

## Slide 121

![Slide 121](images/lec4_p121.png)

### 📝 幻灯片内容

Discussion of CLIP
Computational challenges.
●
Large similarity matrix required for a batch
●
Global normalization
●
Memory intensive

### 💡 通俗解释

*（待补充解释）*

---

## Slide 122

![Slide 122](images/lec4_p122.png)

### 📝 幻灯片内容

Discussion of CLIP
Computational challenges.
●
Large similarity matrix required for a batch
●
Global normalization
●
Memory intensive
Other approach.
●
Reframe 1 ↔ N softmax problem into a 1 ↔ 1 sigmoid one
●
Popular work: Sigmoid Loiss for Language Image Pre-Training
Sigmoid Loss for Language Image Pre-Training, Zhai et al., 2023.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 123

![Slide 123](images/lec4_p123.png)

### 📝 幻灯片内容

From pixel to latent space
Latent diﬀusion models
Text representation
Image representation
Contrastive learning
Guidance
Diﬀusion & 
Large Vision 
Models

### 💡 通俗解释

*（待补充解释）*

---

## Slide 124

![Slide 124](images/lec4_p124.png)

### 📝 幻灯片内容

Today's lecture: Part 3
A teddy bear 
reading a book
Condition
Black box 
architecture
Today's lecture: Multimodal guided generation
Representation
Guided generation
3
1
2

### 💡 通俗解释

*（待补充解释）*

---

## Slide 125

![Slide 125](images/lec4_p125.png)

### 💡 通俗解释

*（待补充解释）*

---

## Slide 126

![Slide 126](images/lec4_p126.png)

### 📝 幻灯片内容

First idea: guide the generation with a classiﬁer
Idea. Use a classiﬁer’s knowledge to feed image generation with information on 
the target class.
Diﬀusion Models Beat GANs on Image Synthesis, Dhariwal et al., 2021.
generation weights
classiﬁer weights

### 💡 通俗解释

*（待补充解释）*

---

## Slide 127

![Slide 127](images/lec4_p127.png)

### 📝 幻灯片内容

Justiﬁcation: Apply conditional Bayes’ rule on
We want to compute
Main derivation
Diﬀusion Models Beat GANs on Image Synthesis, Dhariwal et al., 2021.
Same distribution as
with

### 💡 通俗解释

*（待补充解释）*

---

## Slide 128

![Slide 128](images/lec4_p128.png)

### 📝 幻灯片内容

Justiﬁcation: Apply conditional Bayes’ rule on
We want to compute
Main derivation
Diﬀusion Models Beat GANs on Image Synthesis, Dhariwal et al., 2021.
Same distribution as
with

### 💡 通俗解释

*（待补充解释）*

---

## Slide 129

![Slide 129](images/lec4_p129.png)

### 📝 幻灯片内容

Justiﬁcation: 
Justiﬁcation: Lecture 1’s derivation of the DDPM generation 
process.
Same distribution as
Let’s focus on
Detour 1
Diﬀusion Models Beat GANs on Image Synthesis, Dhariwal et al., 2021.
+ constant

### 💡 通俗解释

*（待补充解释）*

---

## Slide 130

![Slide 130](images/lec4_p130.png)

### 📝 幻灯片内容

Justiﬁcation: Apply conditional Bayes’ rule on
We want to compute
Main derivation
Diﬀusion Models Beat GANs on Image Synthesis, Dhariwal et al., 2021.
Same distribution as
with

### 💡 通俗解释

*（待补充解释）*

---

## Slide 131

![Slide 131](images/lec4_p131.png)

### 📝 幻灯片内容

Let’s focus on
Justiﬁcation: First-order Taylor approximation
Detour 2
Diﬀusion Models Beat GANs on Image Synthesis, Dhariwal et al., 2021.
+ constant

### 💡 通俗解释

*（待补充解释）*

---

## Slide 132

![Slide 132](images/lec4_p132.png)

### 📝 幻灯片内容

Justiﬁcation: Plug in expressions into
and recognize probability density function of a normal distribution 
Justiﬁcation: Apply conditional Bayes’ rule on
We want to compute
Main derivation
Diﬀusion Models Beat GANs on Image Synthesis, Dhariwal et al., 2021.
Same distribution as
with
shifted mean

### 💡 通俗解释

*（待补充解释）*

---

## Slide 133

![Slide 133](images/lec4_p133.png)

### 📝 幻灯片内容

And what about the training loss?
Observe that the per-step generation rule only needs:
●
The unconditioned generation model’s predictions and parameters
Diﬀusion Models Beat GANs on Image Synthesis, Dhariwal et al., 2021.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 134

![Slide 134](images/lec4_p134.png)

### 📝 幻灯片内容

And what about the training loss?
Observe that the per-step generation rule only needs:
●
The unconditioned generation model’s predictions and parameters
●
The classiﬁer’s score
Diﬀusion Models Beat GANs on Image Synthesis, Dhariwal et al., 2021.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 135

![Slide 135](images/lec4_p135.png)

### 📝 幻灯片内容

Training
Generation model.
●
No retraining needed of an unconditioned generation model.
●
Purely a sampling technique.
Classiﬁer.
●
Needs to be trained with cross-entropy loss on noisy images
●
Sample         and train                       to predict the correct label

### 💡 通俗解释

*（待补充解释）*

---

## Slide 136

![Slide 136](images/lec4_p136.png)

### 📝 幻灯片内容

Giving more weight to the condition signal
Empirically, we observe that we need                for good conditioned samples.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 137

![Slide 137](images/lec4_p137.png)

### 📝 幻灯片内容

Limitations
New prerequisites.
●
Classiﬁer been trained on labeled data
●
Need to operate on noised input: cannot use out-of-the-box classiﬁer
●
Distribution of data between two models to be aligned

### 💡 通俗解释

*（待补充解释）*

---

## Slide 138

![Slide 138](images/lec4_p138.png)

### 📝 幻灯片内容

Limitations
New prerequisites.
●
Classiﬁer been trained on labeled data
●
Need to operate on noised input: cannot use out-of-the-box classiﬁer
●
Distribution of data between two models to be aligned
Computational considerations.
●
Extra classiﬁer pass needed at each step
●
New gradient signal needs scaling tuning
●
Taylor expansion introduces approximations

### 💡 通俗解释

*（待补充解释）*

---

## Slide 139

![Slide 139](images/lec4_p139.png)

### 📝 幻灯片内容

Reﬁned goal
generation weights only

### 💡 通俗解释

*（待补充解释）*

---

## Slide 140

![Slide 140](images/lec4_p140.png)

### 📝 幻灯片内容

Any way to get rid of the classiﬁer part?
Motivation.
●
Classiﬁer on noisy data not found in the wild
●
We want to avoid extra model calls at inference time
Classiﬁer-Free Diﬀusion Guidance, Ho et al., 2022.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 141

![Slide 141](images/lec4_p141.png)

### 📝 幻灯片内容

Any way to get rid of the classiﬁer part?
Motivation.
●
Classiﬁer on noisy data not found in the wild
●
We want to avoid extra model calls at inference time
Classiﬁer-Free Diﬀusion Guidance, Ho et al., 2022.
Observation. Conditional and unconditional signal deﬁnes an implicit classiﬁer!
proportional to

### 💡 通俗解释

*（待补充解释）*

---

## Slide 142

![Slide 142](images/lec4_p142.png)

### 📝 幻灯片内容

Change of mindset
Idea. Compute both conditioned and unconditioned situations and infer classiﬁer 
signal. 
Classiﬁer-Free Diﬀusion Guidance, Ho et al., 2022.
classiﬁer-based
classiﬁer-free

### 💡 通俗解释

*（待补充解释）*

---

## Slide 143

![Slide 143](images/lec4_p143.png)

### 📝 幻灯片内容

Training for classiﬁer-free guidance
Classiﬁer-Free Diﬀusion Guidance, Ho et al., 2022.
1. Sample:
time step
noise
clean image
noised image
2. Use
via
and
to predict
3. Compute loss
and backpropagate through

### 💡 通俗解释

*（待补充解释）*

---

## Slide 144

![Slide 144](images/lec4_p144.png)

### 📝 幻灯片内容

Training for classiﬁer-free guidance
Classiﬁer-Free Diﬀusion Guidance, Ho et al., 2022.
1. Sample:
time step
noise
clean image
noised image
2. Use
via
and
to predict
3. Compute loss
and backpropagate through

### 💡 通俗解释

*（待补充解释）*

---

## Slide 145

![Slide 145](images/lec4_p145.png)

### 📝 幻灯片内容

Sampling for classiﬁer-free guidance
Classiﬁer-Free Diﬀusion Guidance, Ho et al., 2022.
unconditioned sample
conditioned sample
guided sample

### 💡 通俗解释

*（待补充解释）*

---

## Slide 146

![Slide 146](images/lec4_p146.png)

### 📝 幻灯片内容

Practical considerations
Modeling.
●
Flexibility of conditioning
●
CLIP embeddings handy to represent conditioning signal
●
Best results with                   and 
Classiﬁer-Free Diﬀusion Guidance, Ho et al., 2022.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 147

![Slide 147](images/lec4_p147.png)

### 📝 幻灯片内容

Practical considerations
Modeling.
●
Flexibility of conditioning
●
CLIP embeddings handy to represent conditioning signal
●
Best results with                   and 
Computational.
●
No more bespoke classiﬁer needed...
●
...but still two calls per step!
Classiﬁer-Free Diﬀusion Guidance, Ho et al., 2022.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 148

![Slide 148](images/lec4_p148.png)

### 💡 通俗解释

*（待补充解释）*

---
