# Stanford CME 296 - Lecture 7: Evaluation (FID, CLIPScore, MLLM-as-a-Judge)

> **课程**: Stanford CME 296 - Diffusion & Large Vision Models
> **讲师**: Afshine Amidi & Shervine Amidi
> **视频**: [YouTube 1:41:12](https://www.youtube.com/watch?v=iNaRBp4T57Q&list=PLoROMvodv4rNdy8rt2rZ4T2xM0OjADnfu&index=7)
> **Slides PDF**: [spring26-cme296-lecture7.pdf](../spring26-cme296-lecture7.pdf)
> **总页数**: 137 页幻灯片

---

## Slide 1

![Slide 1](images/lec7_p001.png)

### 📝 幻灯片内容

CME 296: Diﬀusion &
Large Vision Models
Afshine Amidi & Shervine Amidi
Lecture 7

### 💡 通俗解释

*（待补充解释）*

---

## Slide 2

![Slide 2](images/lec7_p002.png)

### 💡 通俗解释

*（待补充解释）*

---

## Slide 3

![Slide 3](images/lec7_p003.png)

### 📝 幻灯片内容

Recap of last episode…
Logit-Normal distribution
Figure from Scaling Rectiﬁed Flow Transformers for High-Resolution Image Synthesis, Esser et al., 2024.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 4

![Slide 4](images/lec7_p004.png)

### 📝 幻灯片内容

Recap of last episode…
Logit-Normal distribution
Figure from Scaling Rectiﬁed Flow Transformers for High-Resolution Image Synthesis, Esser et al., 2024.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 5

![Slide 5](images/lec7_p005.png)

### 📝 幻灯片内容

Recap of last episode…
Pre-training
🖼
Learn how to 
generate images
1

### 💡 通俗解释

*（待补充解释）*

---

## Slide 6

![Slide 6](images/lec7_p006.png)

### 📝 幻灯片内容

Recap of last episode…
Pre-training
Post-training
🖼
😃
Learn how to 
generate images
Learn how to 
generate good 
images
1
2

### 💡 通俗解释

*（待补充解释）*

---

## Slide 7

![Slide 7](images/lec7_p007.png)

### 📝 幻灯片内容

Recap of last episode…
Pre-training
Post-training
Tuning
🖼
😃
⚙
Learn how to 
generate images
Learn how to 
generate good 
images
Learn how to 
generate images 
for a special case
1
2
3

### 💡 通俗解释

*（待补充解释）*

---

## Slide 8

![Slide 8](images/lec7_p008.png)

### 📝 幻灯片内容

Recap of last episode…
Pre-training
Post-training
Tuning
Distillation
⚡
🖼
😃
⚙
Learn how to 
generate images
Learn how to 
generate good 
images
Learn how to 
generate images 
for a special case
Learn how to 
generate images, 
fast
1
2
3
4

### 💡 通俗解释

*（待补充解释）*

---

## Slide 9

![Slide 9](images/lec7_p009.png)

### 📝 幻灯片内容

Today's lecture
A teddy bear 
reading a book
Generation 
model
Today's lecture: Evaluation
Evaluation

### 💡 通俗解释

*（待补充解释）*

---

## Slide 10

![Slide 10](images/lec7_p010.png)

### 📝 幻灯片内容

Setup
Input prompt
A teddy bear 
reading a book
Image
Generation 
model

### 💡 通俗解释

*（待补充解释）*

---

## Slide 11

![Slide 11](images/lec7_p011.png)

### 📝 幻灯片内容

Motivating example
Generated image
Generation 
model
Input prompt
A teddy bear 
reading a book
Image generated with ChatGPT on May 17th, 2026.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 12

![Slide 12](images/lec7_p012.png)

### 📝 幻灯片内容

Motivating example: does not look real / high quality!
Generation 
model
Input prompt
A teddy bear 
reading a book
Image generated with ChatGPT on May 17th, 2026.
❌
Generated image

### 💡 通俗解释

*（待补充解释）*

---

## Slide 13

![Slide 13](images/lec7_p013.png)

### 📝 幻灯片内容

Motivating example
Generated image
Generation 
model
Input prompt
A teddy bear 
reading a book
Image generated with ChatGPT on May 17th, 2026.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 14

![Slide 14](images/lec7_p014.png)

### 📝 幻灯片内容

Motivating example: does not follow prompt!
Generated image
Generation 
model
Input prompt
A teddy bear 
reading a book
❌
Image generated with ChatGPT on May 17th, 2026.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 15

![Slide 15](images/lec7_p015.png)

### 📝 幻灯片内容

Motivating example
Generation 
model
Input prompt
A teddy bear 
reading a book
Generated image
Image generated with ChatGPT on May 17th, 2026.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 16

![Slide 16](images/lec7_p016.png)

### 📝 幻灯片内容

Motivating example: follows prompt and high quality!
Generation 
model
Input prompt
A teddy bear 
reading a book
✅
Image generated with ChatGPT on May 17th, 2026.
Generated image

### 💡 通俗解释

*（待补充解释）*

---

## Slide 17

![Slide 17](images/lec7_p017.png)

### 📝 幻灯片内容

Tractable scope
Aesthetics
"Is this a good picture?"
●
Physical plausibility
●
Cleanliness
●
Perceptual quality
●
Realism
Image generated with ChatGPT on May 17th, 2026.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 18

![Slide 18](images/lec7_p018.png)

### 📝 幻灯片内容

Tractable scope
Aesthetics
"Is this a good picture?"
Prompt adherence
"Did it follow instructions?"
●
Physical plausibility
●
Cleanliness
●
Perceptual quality
●
Realism
●
Object recall
●
Counting
●
Text rendering
●
Style adherence
A teddy bear 
reading a book
Image generated with ChatGPT on May 17th, 2026.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 19

![Slide 19](images/lec7_p019.png)

### 📝 幻灯片内容

…but not exhaustive!
Other notable dimensions.
●
🛡 Safety
●
🧩 Diversity
●
🧠 Memorization
●
🔍 Bias

### 💡 通俗解释

*（待补充解释）*

---

## Slide 20

![Slide 20](images/lec7_p020.png)

### 📝 幻灯片内容

Human ratings
Reference-free metrics
Reference-based metrics
Multimodal LLMs
MLLM-as-a-Judge
Benchmarks
Diﬀusion & 
Large Vision 
Models

### 💡 通俗解释

*（待补充解释）*

---

## Slide 21

![Slide 21](images/lec7_p021.png)

### 📝 幻灯片内容

Attempt 1: rate images on a scale
A teddy bear reading a book
Very good
Good
Neutral
Bad
Very bad
⚖
Image generated with ChatGPT on May 17th, 2026.
Model A
5
4
3
2
1

### 💡 通俗解释

*（待补充解释）*

---

## Slide 22

![Slide 22](images/lec7_p022.png)

### 📝 幻灯片内容

Attempt 1: rate images on a scale
A teddy bear reading a book
Very good
Good
Neutral
Bad
Very bad
⚖
Image generated with ChatGPT on May 17th, 2026.
Model A
4
3
2
1
5

### 💡 通俗解释

*（待补充解释）*

---

## Slide 23

![Slide 23](images/lec7_p023.png)

### 📝 幻灯片内容

Attempt 1: rate images on a scale
Score
Average of ratings
Discussion.
●
Good to have nuance in score
●
Ratings may be noisy
●
Hard to rate on an absolute scale
Sum of ratings
Number of ratings

### 💡 通俗解释

*（待补充解释）*

---

## Slide 24

![Slide 24](images/lec7_p024.png)

### 📝 幻灯片内容

Attempt 2: rate images on a binary scale
Good
Bad
or
A teddy bear reading a book
Image generated with ChatGPT on May 17th, 2026.
1
0
Model A

### 💡 通俗解释

*（待补充解释）*

---

## Slide 25

![Slide 25](images/lec7_p025.png)

### 📝 幻灯片内容

Attempt 2: rate images on a binary scale
Good
Bad
or
A teddy bear reading a book
Image generated with ChatGPT on May 17th, 2026.
1
0
Model A

### 💡 通俗解释

*（待补充解释）*

---

## Slide 26

![Slide 26](images/lec7_p026.png)

### 📝 幻灯片内容

Attempt 2: rate images on a binary scale
Discussion.
●
Easier task compared to nuanced scale
●
Still hard to rate on an absolute scale
Score
Proportion of pass
Sum of ratings
Number of ratings

### 💡 通俗解释

*（待补充解释）*

---

## Slide 27

![Slide 27](images/lec7_p027.png)

### 📝 幻灯片内容

Attempt 3: rate images via pairwise comparisons
A teddy bear reading a book
>
=
<
Images generated with ChatGPT on May 17th, 2026.
Model A
Model B

### 💡 通俗解释

*（待补充解释）*

---

## Slide 28

![Slide 28](images/lec7_p028.png)

### 📝 幻灯片内容

Attempt 3: rate images via pairwise comparisons
A teddy bear reading a book
Images generated with ChatGPT on May 17th, 2026.
Model A
Model B
>
=
<

### 💡 通俗解释

*（待补充解释）*

---

## Slide 29

![Slide 29](images/lec7_p029.png)

### 📝 幻灯片内容

Win rate
Score
Win rate
Number of wins
Number of comparisons
Discussion.
●
Much easier task than absolute scale!
●
Win rate depends on who we are comparing with who…

### 💡 通俗解释

*（待补充解释）*

---

## Slide 30

![Slide 30](images/lec7_p030.png)

### 📝 幻灯片内容

Cases where win rate is not great…
Artiﬁcial Analysis Image Arena Leaderboard, edited screenshot taken on May 17th, 2026.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 31

![Slide 31](images/lec7_p031.png)

### 📝 幻灯片内容

…and intuition behind how to ﬁx this!
Objective.
Compute win rate… by taking into account "strength" of opponent!
Sure, Model A won. So what? 🤷
>
Images generated with ChatGPT on May 17th, 2026.
Model A
Bad model

### 💡 通俗解释

*（待补充解释）*

---

## Slide 32

![Slide 32](images/lec7_p032.png)

### 📝 幻灯片内容

…and intuition behind how to ﬁx this!
Objective.
Compute win rate… by taking into account "strength" of opponent!
Sure, Model A won. So what? 🤷
WOW, Model A won!!!! 🎉
>
>
Images generated with ChatGPT on May 17th, 2026.
Model A
Bad model
Model A
Good model

### 💡 通俗解释

*（待补充解释）*

---

## Slide 33

![Slide 33](images/lec7_p033.png)

### 📝 幻灯片内容

Elo score
Model A
Bad model
Compute expected score
1

### 💡 通俗解释

*（待补充解释）*

---

## Slide 34

![Slide 34](images/lec7_p034.png)

### 📝 幻灯片内容

Elo score
Compute expected score
Obtain actual score
1
2
Loss
Win
Tie
Model A
Bad model

### 💡 通俗解释

*（待补充解释）*

---

## Slide 35

![Slide 35](images/lec7_p035.png)

### 📝 幻灯片内容

Elo score
Compute expected score
Obtain actual score
Compare actual score with expected score
1
2
3
Model A
Bad model
if Model A wins
if there is a tie
if Model A loses

### 💡 通俗解释

*（待补充解释）*

---

## Slide 36

![Slide 36](images/lec7_p036.png)

### 📝 幻灯片内容

Elo score
Compute expected score
Obtain actual score
Compare actual score with expected score
1
2
Update rating
3
4
Model A
Bad model

### 💡 通俗解释

*（待补充解释）*

---

## Slide 37

![Slide 37](images/lec7_p037.png)

### 📝 幻灯片内容

Leaderboard of text-to-image models
Artiﬁcial Analysis Image Arena Leaderboard, screenshot taken on May 17th, 2026.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 38

![Slide 38](images/lec7_p038.png)

### 📝 幻灯片内容

Limitations with human ratings
●
💸 Expensive
●
🐌 Slow
●
❌ Not necessarily ground truth (fatigue, cultural bias)
●
🤷 Subjective

### 💡 通俗解释

*（待补充解释）*

---

## Slide 39

![Slide 39](images/lec7_p039.png)

### 📝 幻灯片内容

Human ratings
Reference-free metrics
Reference-based metrics
Multimodal LLMs
MLLM-as-a-Judge
Benchmarks
Diﬀusion & 
Large Vision 
Models

### 💡 通俗解释

*（待补充解释）*

---

## Slide 40

![Slide 40](images/lec7_p040.png)

### 📝 幻灯片内容

Motivation
Input prompt
A teddy bear 
reading a book
Valid generated 
images
Generation 
model
Many valid 
images!
Images generated with ChatGPT on May 17th, 2026.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 41

![Slide 41](images/lec7_p041.png)

### 📝 幻灯片内容

Motivation
Input prompt
A teddy bear 
reading a book
Valid generated 
images
Generation 
model
Many valid 
images!
Unfair to compare to a single image!
Images generated with ChatGPT on May 17th, 2026.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 42

![Slide 42](images/lec7_p042.png)

### 📝 幻灯片内容

Back to our problem
Generated image
Generation 
model
Input prompt
A teddy bear 
reading a book
Image generated with ChatGPT on May 17th, 2026.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 43

![Slide 43](images/lec7_p043.png)

### 📝 幻灯片内容

Back to our problem
Generated image
Generation 
model
Input prompt
A teddy bear 
reading a book
1
Aesthetics
Image generated with ChatGPT on May 17th, 2026.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 44

![Slide 44](images/lec7_p044.png)

### 📝 幻灯片内容

Aesthetics
Real image
Generated image
Image generated with ChatGPT on May 17th, 2026.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 45

![Slide 45](images/lec7_p045.png)

### 📝 幻灯片内容

Aesthetics
Real image distribution
Generated image distribution
Image generated with ChatGPT on May 17th, 2026.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 46

![Slide 46](images/lec7_p046.png)

### 📝 幻灯片内容

Aesthetics
Real image distribution
Generated image distribution
?
Image generated with ChatGPT on May 17th, 2026.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 47

![Slide 47](images/lec7_p047.png)

### 📝 幻灯片内容

Aesthetics
Pre-trained 
encoder
Pre-trained 
encoder
Real image 
distribution
Generated image 
distribution
Image generated with ChatGPT on May 17th, 2026.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 48

![Slide 48](images/lec7_p048.png)

### 📝 幻灯片内容

Aesthetics
Pre-trained 
encoder
Pre-trained 
encoder
Real image 
distribution
Generated image 
distribution
Image generated with ChatGPT on May 17th, 2026.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 49

![Slide 49](images/lec7_p049.png)

### 📝 幻灯片内容

Aesthetics
Pre-trained 
encoder
Pre-trained 
encoder
Real image 
distribution
Generated image 
distribution
Image generated with ChatGPT on May 17th, 2026.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 50

![Slide 50](images/lec7_p050.png)

### 📝 幻灯片内容

Aesthetics
Pre-trained 
encoder
Pre-trained 
encoder
Real image 
distribution
Generated image 
distribution
Image generated with ChatGPT on May 17th, 2026.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 51

![Slide 51](images/lec7_p051.png)

### 📝 幻灯片内容

Distance between real and generated distributions
GANs Trained by a Two Time-Scale Update Rule Converge to a Local Nash Equilibrium, Heusel et al., 2017.
Idea. Quantify distance between generated and real images
Location diﬀerence
Shape diﬀerence

### 💡 通俗解释

*（待补充解释）*

---

## Slide 52

![Slide 52](images/lec7_p052.png)

### 📝 幻灯片内容

Fréchet inception distance
GANs Trained by a Two Time-Scale Update Rule Converge to a Local Nash Equilibrium, Heusel et al., 2017.
FID = Fréchet Inception Distance
Idea. Quantify distance between generated and real images
Location diﬀerence
Shape diﬀerence
The lower, the better!

### 💡 通俗解释

*（待补充解释）*

---

## Slide 53

![Slide 53](images/lec7_p053.png)

### 📝 幻灯片内容

We already saw plots using FID in the class!
Lecture 5
Lecture 6
Figure from Scalable Diﬀusion Models with Transformers, Peebles et al., 2022.
Figure from Representation Alignment for Generation: Training Diﬀusion Transformers Is Easier Than You Think, Yu et al., 2024.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 54

![Slide 54](images/lec7_p054.png)

### 📝 幻灯片内容

Discussion on the FID
What it measures.
●
Location diﬀerence. Quality, style
●
Shape diﬀerence. Diversity, variety

### 💡 通俗解释

*（待补充解释）*

---

## Slide 55

![Slide 55](images/lec7_p055.png)

### 📝 幻灯片内容

Discussion on the FID
What it measures.
●
Location diﬀerence. Quality, style
●
Shape diﬀerence. Diversity, variety
Discussion. Depends on:
●
Sample size (common: FID-50k)
●
Reference data distribution
●
Normality assumption

### 💡 通俗解释

*（待补充解释）*

---

## Slide 56

![Slide 56](images/lec7_p056.png)

### 📝 幻灯片内容

Back to our problem
Generated image
Generation 
model
Input prompt
A teddy bear 
reading a book
1
Aesthetics
2
Prompt adherence
Image generated with ChatGPT on May 17th, 2026.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 57

![Slide 57](images/lec7_p057.png)

### 📝 幻灯片内容

Reminder from Lecture 4: CLIP!
CLIP = Contrastive Language-Image Pretraining
Learning Transferable Visual Models From Natural Language Supervision, Radford et al., 2021

### 💡 通俗解释

*（待补充解释）*

---

## Slide 58

![Slide 58](images/lec7_p058.png)

### 📝 幻灯片内容

Image-text alignment via CLIPScore
CLIPScore: A Reference-free Evaluation Metric for Image Captioning, Hessel et al., 2021.
A teddy bear 
reading a book
CLIPScore
Alignment between text and image
Raw CLIP model

### 💡 通俗解释

*（待补充解释）*

---

## Slide 59

![Slide 59](images/lec7_p059.png)

### 📝 幻灯片内容

Human preference with PickScore
Pick-a-Pic: An Open Dataset of User Preferences for Text-to-Image Generation, Kirstain et al., 2023.
A teddy bear 
reading a book
PickScore
Human preference
CLIP model trained on preference data

### 💡 通俗解释

*（待补充解释）*

---

## Slide 60

![Slide 60](images/lec7_p060.png)

### 📝 幻灯片内容

Human ratings
Reference-free metrics
Reference-based metrics
Multimodal LLMs
MLLM-as-a-Judge
Benchmarks
Diﬀusion & 
Large Vision 
Models

### 💡 通俗解释

*（待补充解释）*

---

## Slide 61

![Slide 61](images/lec7_p061.png)

### 📝 幻灯片内容

Cases where reference image is available
Encoder
Decoder
Reconstructed 
input 
Original
input 
Other tasks where reference is available. Image editing, distillation
Image generated with ChatGPT on May 17th, 2026.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 62

![Slide 62](images/lec7_p062.png)

### 📝 幻灯片内容

Notations
Original
input 
Reconstructed 
input 
Image generated with ChatGPT on May 17th, 2026.
?

### 💡 通俗解释

*（待补充解释）*

---

## Slide 63

![Slide 63](images/lec7_p063.png)

### 📝 幻灯片内容

Pixel-wise comparisons
Idea. Pixel-wise distance
MSE = Mean Squared Error
Discussion. Not interpretable and sensitive to pixel position

### 💡 通俗解释

*（待补充解释）*

---

## Slide 64

![Slide 64](images/lec7_p064.png)

### 📝 幻灯片内容

PSNR = Peak Signal-to-Noise Ratio
Pixel-wise comparisons
Idea. Normalized pixel-wise distance
Discussion. More interpretable but still sensitive to pixel position

### 💡 通俗解释

*（待补充解释）*

---

## Slide 65

![Slide 65](images/lec7_p065.png)

### 📝 幻灯片内容

Structure comparison
Original
input 
Reconstructed 
input

### 💡 通俗解释

*（待补充解释）*

---

## Slide 66

![Slide 66](images/lec7_p066.png)

### 📝 幻灯片内容

Structure comparison
Original
input 
Reconstructed 
input

### 💡 通俗解释

*（待补充解释）*

---

## Slide 67

![Slide 67](images/lec7_p067.png)

### 📝 幻灯片内容

Structure comparison
Mean
Variance
Covariance
●
Luminance. Same brightness?
●
Contrast. Same variance?
●
Structure. Correlation between pixels?

### 💡 通俗解释

*（待补充解释）*

---

## Slide 68

![Slide 68](images/lec7_p068.png)

### 📝 幻灯片内容

Structure comparison
●
Luminance similarity

### 💡 通俗解释

*（待补充解释）*

---

## Slide 69

![Slide 69](images/lec7_p069.png)

### 📝 幻灯片内容

Structure comparison
●
Luminance similarity
●
Contrast similarity

### 💡 通俗解释

*（待补充解释）*

---

## Slide 70

![Slide 70](images/lec7_p070.png)

### 📝 幻灯片内容

Structure comparison
●
Luminance similarity
●
Contrast similarity
●
Structure similarity

### 💡 通俗解释

*（待补充解释）*

---

## Slide 71

![Slide 71](images/lec7_p071.png)

### 📝 幻灯片内容

Structure comparison
●
Luminance similarity
●
Contrast similarity
●
Structure similarity

### 💡 通俗解释

*（待补充解释）*

---

## Slide 72

![Slide 72](images/lec7_p072.png)

### 📝 幻灯片内容

Structure comparison
Luminance similarity
Contrast similarity
Structure similarity

### 💡 通俗解释

*（待补充解释）*

---

## Slide 73

![Slide 73](images/lec7_p073.png)

### 💡 通俗解释

*（待补充解释）*

---

## Slide 74

![Slide 74](images/lec7_p074.png)

### 📝 幻灯片内容

Structure comparison
Original
input 
Reconstructed 
input

### 💡 通俗解释

*（待补充解释）*

---

## Slide 75

![Slide 75](images/lec7_p075.png)

### 📝 幻灯片内容

SSIM = Structural SIMilarity
Image Quality Assessment: From Error Visibility to Structural Similarity, Wang et al., 2004.
Structure comparison
Idea. Measure structural similarity by comparing patch statistics
Limitations. Still vulnerable to "spatial shift"

### 💡 通俗解释

*（待补充解释）*

---

## Slide 76

![Slide 76](images/lec7_p076.png)

### 📝 幻灯片内容

LPIPS = Learned Perceptual Image Patch Similarity
The Unreasonable Eﬀectiveness of Deep Features as a Perceptual Metric, Zhang et al., 2018.
Feature comparison
Idea. Use pre-trained model to compute features that align with visual perception
Limitations. Not directly interpretable

### 💡 通俗解释

*（待补充解释）*

---

## Slide 77

![Slide 77](images/lec7_p077.png)

### 📝 幻灯片内容

Human ratings
Reference-free metrics
Reference-based metrics
Multimodal LLMs
MLLM-as-a-Judge
Benchmarks
Diﬀusion & 
Large Vision 
Models

### 💡 通俗解释

*（待补充解释）*

---

## Slide 78

![Slide 78](images/lec7_p078.png)

### 📝 幻灯片内容

Objective
Gap. Fixed metrics are not interpretable.
●
Many of them
●
Operate at diﬀerent levels
●
Fragmentation of meaning
●
Inevitable misalignments

### 💡 通俗解释

*（待补充解释）*

---

## Slide 79

![Slide 79](images/lec7_p079.png)

### 📝 幻灯片内容

Objective
Gap. Fixed metrics are not interpretable.
●
Many of them
●
Operate at diﬀerent levels
●
Fragmentation of meaning
●
Inevitable misalignments
Detour. Model that "speaks"? LLMs!
Any way to adapt wins to images?

### 💡 通俗解释

*（待补充解释）*

---

## Slide 80

![Slide 80](images/lec7_p080.png)

### 📝 幻灯片内容

Objective
Figures adapted from Attention Is All You Need, Vaswani et al., 2017, Scalable Diﬀusion Models with Transformers, Peebles et al., 2022,
Scaling Rectiﬁed Flow Transformers for High-Resolution Image Synthesis, Esser et al., 2024.
Transformer
DiT
MM-DiT

### 💡 通俗解释

*（待补充解释）*

---

## Slide 81

![Slide 81](images/lec7_p081.png)

### 📝 幻灯片内容

Objective
Figures adapted from Attention Is All You Need, Vaswani et al., 2017, Scalable Diﬀusion Models with Transformers, Peebles et al., 2022,
Scaling Rectiﬁed Flow Transformers for High-Resolution Image Synthesis, Esser et al., 2024.
Transformer
DiT
MM-DiT
text
text

### 💡 通俗解释

*（待补充解释）*

---

## Slide 82

![Slide 82](images/lec7_p082.png)

### 📝 幻灯片内容

Objective
Figures adapted from Attention Is All You Need, Vaswani et al., 2017, Scalable Diﬀusion Models with Transformers, Peebles et al., 2022,
Scaling Rectiﬁed Flow Transformers for High-Resolution Image Synthesis, Esser et al., 2024.
Transformer
DiT
MM-DiT
image
image and/or label
text
text

### 💡 通俗解释

*（待补充解释）*

---

## Slide 83

![Slide 83](images/lec7_p083.png)

### 📝 幻灯片内容

Objective
Figures adapted from Attention Is All You Need, Vaswani et al., 2017, Scalable Diﬀusion Models with Transformers, Peebles et al., 2022,
Scaling Rectiﬁed Flow Transformers for High-Resolution Image Synthesis, Esser et al., 2024.
Transformer
MM-DiT
image and/or text
image
DiT
image
text
text
image and/or label

### 💡 通俗解释

*（待补充解释）*

---

## Slide 84

![Slide 84](images/lec7_p084.png)

### 📝 幻灯片内容

Objective
text
image and/or text
?

### 💡 通俗解释

*（待补充解释）*

---

## Slide 85

![Slide 85](images/lec7_p085.png)

### 📝 幻灯片内容

Image understanding based on text input
How cute is this teddy bear?
?
Very cute!

### 💡 通俗解释

*（待补充解释）*

---

## Slide 86

![Slide 86](images/lec7_p086.png)

### 📝 幻灯片内容

Tokenization
How cute is this teddy bear?
How
cute
is
this
teddy bear
?

### 💡 通俗解释

*（待补充解释）*

---

## Slide 87

![Slide 87](images/lec7_p087.png)

### 📝 幻灯片内容

Idea 1: leverage the original Transformer!
Figure adapted from Attention Is All You Need, Vaswani et al., 2017.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 88

![Slide 88](images/lec7_p088.png)

### 📝 幻灯片内容

How cute is this teddy bear?
Decoder with 
cross-attention
Very cute!
Idea 1: leverage the original Transformer!

### 💡 通俗解释

*（待补充解释）*

---

## Slide 89

![Slide 89](images/lec7_p089.png)

### 📝 幻灯片内容

Idea. Encode image modality as cross-attention keys/values.
Flamingo: a Visual Language Model for Few-Shot Learning, Alayrac et al., 2022.
Flamingo (2022)
Idea 1: leverage the original Transformer!

### 💡 通俗解释

*（待补充解释）*

---

## Slide 90

![Slide 90](images/lec7_p090.png)

### 📝 幻灯片内容

Idea 2: recycle decoder-only architecture
How cute is this teddy bear?
"Typical" LLM
Very cute!

### 💡 通俗解释

*（待补充解释）*

---

## Slide 91

![Slide 91](images/lec7_p091.png)

### 📝 幻灯片内容

Idea 2: recycle decoder-only architecture
Idea. Just treat it as a regular LLM input!
Visual Instruction Tuning, Liu et al., 2023.
LLaVA (2023)

### 💡 通俗解释

*（待补充解释）*

---

## Slide 92

![Slide 92](images/lec7_p092.png)

### 📝 幻灯片内容

Trends
Architecture. Decoder with joint attention.
Qwen3-VL Technical Report, Bai et al., 2025, GLM-4.5V and GLM-4.1V-Thinking, GLM-V Team, 2025.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 93

![Slide 93](images/lec7_p093.png)

### 📝 幻灯片内容

Trends
Architecture. Decoder with joint attention.
Capabilities.
●
Work across resolutions
●
Spatial awareness
●
OCR
●
Includes other modalities
●
Reasoning
Qwen3-VL Technical Report, Bai et al., 2025, GLM-4.5V and GLM-4.1V-Thinking, GLM-V Team, 2025.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 94

![Slide 94](images/lec7_p094.png)

### 📝 幻灯片内容

Human ratings
Reference-free metrics
Reference-based metrics
Multimodal LLMs
MLLM-as-a-Judge
Benchmarks
Diﬀusion & 
Large Vision 
Models

### 💡 通俗解释

*（待补充解释）*

---

## Slide 95

![Slide 95](images/lec7_p095.png)

### 📝 幻灯片内容

Motivation
Complaint. Traditional metrics are both holistic and opaque.
A cute teddy bear is reading a book
CLIPScore: 0.922
why?

### 💡 通俗解释

*（待补充解释）*

---

## Slide 96

![Slide 96](images/lec7_p096.png)

### 📝 幻灯片内容

TIFA
A cute teddy bear is reading a book
Is there a teddy bear?
TIFA = Text-to-Image Faithfulness Evaluation with QA
TIFA: Accurate and Interpretable Text-to-Image Faithfulness Evaluation with Question Answering, Hu et al., 2023.
Is the teddy bear cute?
Is there a book?
Is the teddy bear reading the 
book?
✅
✅
✅
✅
TIFA: 100.0
Idea. Decompose faithfulness into atomic questions.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 97

![Slide 97](images/lec7_p097.png)

### 📝 幻灯片内容

TIFA
TIFA: Accurate and Interpretable Text-to-Image Faithfulness Evaluation with Question Answering, Hu et al., 2023.
Beneﬁts. 
●
Simple to understand
●
Score debugging is easy

### 💡 通俗解释

*（待补充解释）*

---

## Slide 98

![Slide 98](images/lec7_p098.png)

### 📝 幻灯片内容

TIFA
TIFA: Accurate and Interpretable Text-to-Image Faithfulness Evaluation with Question Answering, Hu et al., 2023.
Beneﬁts. 
●
Simple to understand
●
Score debugging is easy
Drawbacks.
●
Not easy to convey per-claim importance
●
Question generation itself error-prone

### 💡 通俗解释

*（待补充解释）*

---

## Slide 99

![Slide 99](images/lec7_p099.png)

### 📝 幻灯片内容

Motivation
Complaint. Traditional metrics do not carry composition well.
A cute teddy bear is reading a book
A cute book is reading a teddy bear
CLIPScore
≈
CLIPScore

### 💡 通俗解释

*（待补充解释）*

---

## Slide 100

![Slide 100](images/lec7_p100.png)

### 📝 幻灯片内容

VQAScore
Evaluating Text-to-Visual Generation with Image-to-Text Generation, Lin et al., 2024. 
Figure adapted from Super Study Guide: Transformers and Large Language Models, Amidi et al., 2024.
VQAScore = Visual Question Answering Score
[Image] Does this ﬁgure show [Prompt]? Please answer yes or no.
yes
VQAScore

### 💡 通俗解释

*（待补充解释）*

---

## Slide 101

![Slide 101](images/lec7_p101.png)

### 📝 幻灯片内容

Beneﬁt. Leverages LLM-style understanding capabilities.
A cute teddy bear is reading a book
A cute book is reading a teddy bear
VQAScore
>
VQAScore
VQAScore
Evaluating Text-to-Visual Generation with Image-to-Text Generation, Lin et al., 2024.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 102

![Slide 102](images/lec7_p102.png)

### 📝 幻灯片内容

VQAScore
Evaluating Text-to-Visual Generation with Image-to-Text Generation, Lin et al., 2024.
Limitations.
●
Assumes access to token probabilities
●
TIFA + VQAScore means multiple MLLM calls
●
Feels like there should be a more generic approach

### 💡 通俗解释

*（待补充解释）*

---

## Slide 103

![Slide 103](images/lec7_p103.png)

### 📝 幻灯片内容

VQAScore
Limitations.
●
Assumes access to token probabilities
●
TIFA + VQAScore means multiple MLLM calls
●
Feels like there should be a more generic approach
Attractive alternative mindset
Engineer outcome
Infer outcome

### 💡 通俗解释

*（待补充解释）*

---

## Slide 104

![Slide 104](images/lec7_p104.png)

### 📝 幻灯片内容

VIEScore
VIEScore: Towards Explainable Metrics for Conditional Image Synthesis Evaluation, Ku et al., 2023.
VIEScore = Visual Instruction-guided Explainable Score
⚖  MLLM-as-a-Judge
📝 Prompt
🤖 Generated image
🔍 Rubric
🎯 Score
A cute teddy bear is 
reading a book
Semantic consistency
✅
💭 Evidence
A soft, fluffy brown teddy 
bear is sitting on a bed...

### 💡 通俗解释

*（待补充解释）*

---

## Slide 105

![Slide 105](images/lec7_p105.png)

### 📝 幻灯片内容

Dimensions
Example. Rubrics could be:
●
Semantic consistency: How aligned with the conditions?
●
Perceptual quality: How authentic and natural?
VIEScore: Towards Explainable Metrics for Conditional Image Synthesis Evaluation, Ku et al., 2023.
✅ ✅
✅ ❌

### 💡 通俗解释

*（待补充解释）*

---

## Slide 106

![Slide 106](images/lec7_p106.png)

### 📝 幻灯片内容

Structure
Input: A cute teddy bear is reading a book, 
Rubric: Please the input across the following axes
- Dimension 1: Guidelines...
- Dimension 2: Guidelines...
Output: Return the graded result in JSON format: 
{
  "rationale": ...,
  "score": ...,
}
Example of a judge prompt.
How to ensure calibration?

### 💡 通俗解释

*（待补充解释）*

---

## Slide 107

![Slide 107](images/lec7_p107.png)

### 📝 幻灯片内容

Typical workﬂow
MLLM-as-a-Judge
🐇
Seed. Seek human expertise about task at hand.
Image generation
Human ratings
🐢

### 💡 通俗解释

*（待补充解释）*

---

## Slide 108

![Slide 108](images/lec7_p108.png)

### 📝 幻灯片内容

Typical workﬂow
Image generation
🐇
Calibrate. Align MLLM-as-a-Judge with human expertise.
Human ratings
MLLM-as-a-Judge
🐢

### 💡 通俗解释

*（待补充解释）*

---

## Slide 109

![Slide 109](images/lec7_p109.png)

### 📝 幻灯片内容

Typical workﬂow
Human ratings
🐢
Automate. Rely on MLLM-as-a-Judge for general cases.
Image generation
MLLM-as-a-Judge
🐇

### 💡 通俗解释

*（待补充解释）*

---

## Slide 110

![Slide 110](images/lec7_p110.png)

### 📝 幻灯片内容

Use cases
Pointwise
Pairwise
Which one is better:
Response A
or
Response B
?
Response A
Evaluate the quality 
of:
Response
Very good
⚖
⚖
Batch ranking
Rank the following:
Response A
Response B
Response C
...
B → A → C
⚖
MLLM-as-a-Judge: Assessing Multimodal LLM-as-a-Judge with Vision-Language Benchmark, Chen et al., 2024.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 111

![Slide 111](images/lec7_p111.png)

### 📝 幻灯片内容

Use cases
Pointwise
Pairwise
Which one is better:
Response A
or
Response B
?
Response A
Evaluate the quality 
of:
Response
Very good
⚖
⚖
Batch ranking
Rank the following:
Response A
Response B
Response C
...
2/1/3
⚖
great for diagnostics
MLLM-as-a-Judge: Assessing Multimodal LLM-as-a-Judge with Vision-Language Benchmark, Chen et al., 2024.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 112

![Slide 112](images/lec7_p112.png)

### 📝 幻灯片内容

B → A → C
Use cases
Pointwise
Evaluate the quality 
of:
Response
Very good
⚖
Batch ranking
Rank the following:
Response A
Response B
Response C
...
⚖
great for diagnostics
MLLM-as-a-Judge: Assessing Multimodal LLM-as-a-Judge with Vision-Language Benchmark, Chen et al., 2024.
Pairwise
Which one is better:
Response A
or
Response B
?
Response A
⚖
great to compare models

### 💡 通俗解释

*（待补充解释）*

---

## Slide 113

![Slide 113](images/lec7_p113.png)

### 📝 幻灯片内容

Use cases
Pointwise
Pairwise
Which one is better:
Response A
or
Response B
?
Response A
Evaluate the quality 
of:
Response
Very good
⚖
⚖
great to compare models
great for diagnostics
MLLM-as-a-Judge: Assessing Multimodal LLM-as-a-Judge with Vision-Language Benchmark, Chen et al., 2024.
B → A → C
Batch ranking
Rank the following:
Response A
Response B
Response C
...
⚖
sensitive to ordering
not really used in practice

### 💡 通俗解释

*（待补充解释）*

---

## Slide 114

![Slide 114](images/lec7_p114.png)

### 📝 幻灯片内容

Best practices
●
Parse score into atomic criteria

### 💡 通俗解释

*（待补充解释）*

---

## Slide 115

![Slide 115](images/lec7_p115.png)

### 📝 幻灯片内容

Best practices
●
Parse score into atomic criteria
●
Ask MLLM to describe evidence before giving a score

### 💡 通俗解释

*（待补充解释）*

---

## Slide 116

![Slide 116](images/lec7_p116.png)

### 📝 幻灯片内容

Best practices
●
Parse score into atomic criteria
●
Ask MLLM to describe evidence before giving a score
●
Use low temperature and structured outputs

### 💡 通俗解释

*（待补充解释）*

---

## Slide 117

![Slide 117](images/lec7_p117.png)

### 📝 幻灯片内容

Best practices
●
Parse score into atomic criteria
●
Ask MLLM to describe evidence before giving a score
●
Use low temperature and structured outputs
●
Randomize A/B order for pairwise judging

### 💡 通俗解释

*（待补充解释）*

---

## Slide 118

![Slide 118](images/lec7_p118.png)

### 📝 幻灯片内容

Best practices
●
Parse score into atomic criteria
●
Ask MLLM to describe evidence before giving a score
●
Use low temperature and structured outputs
●
Randomize A/B order for pairwise judging
●
Validate judge scores against human ratings before trusting it

### 💡 通俗解释

*（待补充解释）*

---

## Slide 119

![Slide 119](images/lec7_p119.png)

### 📝 幻灯片内容

Human ratings
Reference-free metrics
Reference-based metrics
Multimodal LLMs
MLLM-as-a-Judge
Benchmarks
Diﬀusion & 
Large Vision 
Models

### 💡 通俗解释

*（待补充解释）*

---

## Slide 120

![Slide 120](images/lec7_p120.png)

### 📝 幻灯片内容

Common benchmarks
Object alignment
• Verify objects, 
counts, colors
• Tests compositional 
image generation
• Fine-grained failure 
diagnosis
GenEval

### 💡 通俗解释

*（待补充解释）*

---

## Slide 121

![Slide 121](images/lec7_p121.png)

### 📝 幻灯片内容

Text-to-image alignment example: GenEval
GenEval: An Object-Focused Framework for Evaluating Text-to-Image Alignment, Ghosh et al., 2023.
GenEval = Generation Evaluation
?
Goal. Tests rendering speciﬁc objects and their attributes.
Characteristics:
●
~600 prompts across 6 tasks
●
Tasks: 1/2 objects, counts, colors, position, color attribution
Evaluation criteria. Yes/no per task associated to prompt.
Object detection,
geometry,
color classiﬁcation

### 💡 通俗解释

*（待补充解释）*

---

## Slide 122

![Slide 122](images/lec7_p122.png)

### 📝 幻灯片内容

Text-to-image alignment example: GenEval
GenEval: An Object-Focused Framework for Evaluating Text-to-Image Alignment, Ghosh et al., 2023.
Samples.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 123

![Slide 123](images/lec7_p123.png)

### 📝 幻灯片内容

Common benchmarks
Object alignment
Dense prompts
• Verify objects, 
counts, colors
• Tests compositional 
image generation
• Fine-grained failure 
diagnosis
• Follow long detailed 
prompts
• Track entities, 
attributes, relations
• Evaluates semantic 
completeness
GenEval
DPG-Bench

### 💡 通俗解释

*（待补充解释）*

---

## Slide 124

![Slide 124](images/lec7_p124.png)

### 📝 幻灯片内容

Dense prompt following example: DPG-Bench
DPG-Bench = Dense Prompt Graph Benchmark
Goal. Remembers every detail when given a massive paragraph of text.
Characteristics:
●
Graph of questions derived with the "DSG" pipeline into 
entity/attribute/relation
●
~14,000 questions across ~1,000 prompts
Evaluation criteria. Yes/no to questions in graph.
VQA judge in graph
ELLA: Equip Diﬀusion Models with LLM for Enhanced Semantic Alignment, Hu et al., 2024.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 125

![Slide 125](images/lec7_p125.png)

### 📝 幻灯片内容

Example.
Dense prompt following example: DPG-Bench
ELLA: Equip Diﬀusion Models with LLM for Enhanced Semantic Alignment, Hu et al., 2024.
An empty space where an invisible man would be, with a pair of 
horn-rimmed glasses seemingly floating in mid-air, and a pearl 
bead necklace draped in the space below them. In the space where 
his hands would be, a smartphone is held... the room appears 
ordinary, with a couch and a coffee table nearby, upon which rests 
a scattering of magazines and a remote control.
Empty space?
Invisible man?
Glasses?
Glasses 
horn-rimmed?
Glasses ﬂoating 
in the space?
Room?
Couch?

### 💡 通俗解释

*（待补充解释）*

---

## Slide 126

![Slide 126](images/lec7_p126.png)

### 📝 幻灯片内容

Example.
Dense prompt following example: DPG-Bench
ELLA: Equip Diﬀusion Models with LLM for Enhanced Semantic Alignment, Hu et al., 2024.
An empty space where an invisible man would be, with a pair of 
horn-rimmed glasses seemingly floating in mid-air, and a pearl 
bead necklace draped in the space below them. In the space where 
his hands would be, a smartphone is held... the room appears 
ordinary, with a couch and a coffee table nearby, upon which rests 
a scattering of magazines and a remote control.
Empty space?
Invisible man?
Glasses?
Glasses 
horn-rimmed?
Glasses ﬂoating 
in the space?
Room?
Couch?
Yes/No?

### 💡 通俗解释

*（待补充解释）*

---

## Slide 127

![Slide 127](images/lec7_p127.png)

### 📝 幻灯片内容

Example.
Dense prompt following example: DPG-Bench
ELLA: Equip Diﬀusion Models with LLM for Enhanced Semantic Alignment, Hu et al., 2024.
An empty space where an invisible man would be, with a pair of 
horn-rimmed glasses seemingly floating in mid-air, and a pearl 
bead necklace draped in the space below them. In the space where 
his hands would be, a smartphone is held... the room appears 
ordinary, with a couch and a coffee table nearby, upon which rests 
a scattering of magazines and a remote control.
Empty space?
Invisible man?
Glasses?
Glasses 
horn-rimmed?
Glasses ﬂoating 
in the space?
Room?
Couch?

### 💡 通俗解释

*（待补充解释）*

---

## Slide 128

![Slide 128](images/lec7_p128.png)

### 📝 幻灯片内容

Example.
Dense prompt following example: DPG-Bench
ELLA: Equip Diﬀusion Models with LLM for Enhanced Semantic Alignment, Hu et al., 2024.
An empty space where an invisible man would be, with a pair of 
horn-rimmed glasses seemingly floating in mid-air, and a pearl 
bead necklace draped in the space below them. In the space where 
his hands would be, a smartphone is held... the room appears 
ordinary, with a couch and a coffee table nearby, upon which rests 
a scattering of magazines and a remote control.
Empty space?
Invisible man?
Glasses?
Glasses 
horn-rimmed?
Glasses ﬂoating 
in the space?
Room?
Couch?

### 💡 通俗解释

*（待补充解释）*

---

## Slide 129

![Slide 129](images/lec7_p129.png)

### 📝 幻灯片内容

Example.
Dense prompt following example: DPG-Bench
ELLA: Equip Diﬀusion Models with LLM for Enhanced Semantic Alignment, Hu et al., 2024.
An empty space where an invisible man would be, with a pair of 
horn-rimmed glasses seemingly floating in mid-air, and a pearl 
bead necklace draped in the space below them. In the space where 
his hands would be, a smartphone is held... the room appears 
ordinary, with a couch and a coffee table nearby, upon which rests 
a scattering of magazines and a remote control.
Empty space?
Invisible man?
Glasses?
Glasses 
horn-rimmed?
Glasses ﬂoating 
in the space?
Room?
Couch?

### 💡 通俗解释

*（待补充解释）*

---

## Slide 130

![Slide 130](images/lec7_p130.png)

### 📝 幻灯片内容

Common benchmarks
Object alignment
Dense prompts
Text rendering
• Verify objects, 
counts, colors
• Tests compositional 
image generation
• Fine-grained failure 
diagnosis
• Follow long detailed 
prompts
• Track entities, 
attributes, relations
• Evaluates semantic 
completeness
• Generate readable 
text in images
• Handles long 
strings
• Tests OCR-level 
ﬁdelity
GenEval
DPG-Bench
LongText-Bench

### 💡 通俗解释

*（待补充解释）*

---

## Slide 131

![Slide 131](images/lec7_p131.png)

### 📝 幻灯片内容

Text rendering example: LongText-Bench
LongText-Bench = Long Text-Rendering Benchmark
?
Goal. Render readable multi-line text in images.
Characteristics:
●
160 English + 160 Chinese prompts
●
8 scenarios: signs, labels, printed materials, webpages, slides, posters, 
captions, dialogues.
Evaluation criteria. OCR extraction of rendered text.
OCR match
X-Omni: Reinforcement Learning Makes Discrete Autoregressive Image Generative Models Great Again, Geng et al., 2025.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 132

![Slide 132](images/lec7_p132.png)

### 📝 幻灯片内容

Text rendering example: LongText-Bench
Samples. 
X-Omni: Reinforcement Learning Makes Discrete Autoregressive Image Generative Models Great Again, Geng et al., 2025.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 133

![Slide 133](images/lec7_p133.png)

### 📝 幻灯片内容

Common benchmarks
Object alignment
Dense prompts
Text rendering
Image editing
• Verify objects, 
counts, colors
• Tests compositional 
image generation
• Fine-grained failure 
diagnosis
• Follow long detailed 
prompts
• Track entities, 
attributes, relations
• Evaluates semantic 
completeness
• Generate readable 
text in images
• Handles long 
strings
• Tests OCR-level 
ﬁdelity
• Apply user edit 
instructions
• Preserve source 
image quality
• Covers real-world 
edit types
GenEval
DPG-Bench
LongText-Bench
GEdit-Bench

### 💡 通俗解释

*（待补充解释）*

---

## Slide 134

![Slide 134](images/lec7_p134.png)

### 📝 幻灯片内容

Image editing example: GEdit-Bench
GEdit-Bench = Grounded Edit Benchmark
?
Goal. Edit an image without destroying the original context.
Characteristics:
●
~600 editing examples
●
11 categories: background/color/material/motion/style/text change, 
photoshopping, subject add/remove/replace, tone transfer 
Evaluation criteria. VIEScore-style judge.
MLLM-as-a-Judge
Step1X-Edit: A Practical Framework for General Image Editing, Liu et al., 2025.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 135

![Slide 135](images/lec7_p135.png)

### 📝 幻灯片内容

Image editing example: GEdit-Bench
Step1X-Edit: A Practical Framework for General Image Editing, Liu et al., 2025.
Samples.

### 💡 通俗解释

*（待补充解释）*

---

## Slide 136

![Slide 136](images/lec7_p136.png)

### 📝 幻灯片内容

Last thoughts
Sample images. "See how well my model performs!"
Beware when used as "proof"!

### 💡 通俗解释

*（待补充解释）*

---

## Slide 137

![Slide 137](images/lec7_p137.png)

### 💡 通俗解释

*（待补充解释）*

---
