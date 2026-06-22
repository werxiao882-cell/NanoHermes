# 再读Agentic RL经典综述，讲清楚从LLM RL到Agent RL的演进及生态

![](https://mmbiz.qpic.cn/sz_mmbiz_png/j2RPloCW20piaeicVaDgxTpRtoMJ6ONv69CQqoRdKSyvNMaFNnz6wvVacxDHfgibXuuibcYhPIYytVt6AyUMXldKVn2s49bkzia6ibcI8djribldKw/640?wx_fmt=png&from=appmsg)

![从 LLM RL 到 Agentic RL 的范式转变。扇形设计体现了 RL 表述的向外扩展——从传统 RL（内层），到 LLM RL，再到完整的 Agentic RL（外层）。颜色编码区域表示：红色 = LLM RL 特有功能；蓝绿色 = AgenticRL 所需功能；紫色 = 现有 Agentic RL 实现。箭头向外指，表示在迈向更具智能体特性的设置时，交互广度（工具使用、网页浏览、动态环境）不断增加](https://mmbiz.qpic.cn/mmbiz_jpg/j2RPloCW20oaKLUSwQvLGiaw70tYicYibbN315V6qBmnT9XOGadZn30GFgmVj6uBUryymRVKAHbz2hVUOqElDKQiavO11QBHjibgbicicnnQick3hyI/640?wx_fmt=jpeg&from=appmsg)

![](https://mmbiz.qpic.cn/sz_mmbiz_jpg/j2RPloCW20qG8lTJ4D0Igr70RAdSTUHicrEg94KSThnQMhDBqPxibB3hn2tBuOvJFKIrRDuytta0v9OHpFTASPic8jtiaNTYcm7NZWhJVTulMzk/640?wx_fmt=jpeg&from=appmsg)

![PPO、DPO 与 GRPO 系列主流变体的对比。Clip 指将策略比值限制在 1 附近，防止其变动过大，从而保证更新稳定；KLpenalty 指对学习策略与参考策略之间的 KL 散度施加惩罚，以确保对齐](https://mmbiz.qpic.cn/mmbiz_jpg/j2RPloCW20oPDuoRrS8xHLxSqBUcamicBQyvLDiaJl5ygmErFic3MYFsZ7jIJU9HazdxQOZHLqjZgGf6m0eicVFpQqhvBnVKkOeYpNom9v3Mbe0/640?wx_fmt=jpeg&from=appmsg)

![面向智能体 LLM 的智能体–环境交互与 RL 循环。核心智能体能力驱动动作生成，环境提供反馈与奖励，这些通过基于 RL
的优化在多样化任务域中聚合（“Collab.”表示需要显式任务划分与多智能体协调的任务）](https://mmbiz.qpic.cn/mmbiz_jpg/j2RPloCW20r1NsT0GpXsWqRBquGolOCticWtKOrnPU1EJjwaRQMAf1w426B12REGdFx5Fk48AavGwyLPHTUnQKe3ESZNIZD9RAQEfra3kGOY/640?wx_fmt=jpeg&from=appmsg)

![智能体工具使用的发展](https://mmbiz.qpic.cn/sz_mmbiz_png/j2RPloCW20pLS8HaoNFSDx6NZY9UlUJzkeX4DETOrrJJPXbQ5OsNaiatk8GRMRo41BVGAg9sg5feMpZbia7w2LTqRFSpChokUdqby4X5SnFSs/640?wx_fmt=png&from=appmsg)

![三类经典智能体Memory方案](https://mmbiz.qpic.cn/mmbiz_jpg/j2RPloCW20ptAPSyuOvcTPEVhKwChqibicg0Z6Sibl8BichH6EuFAjeBUoKYbzCqnobOHyL8Uiaib98DT1LDW0Hbra2DROU7ka04J9c8pMeNz0wxY/640?wx_fmt=jpeg&from=appmsg)

![RL 如何在六大核心能力上赋能智能体 LLM 的概览。中央面板汇总能力分类，侧面板展示代表性 RL 机制与交互模式。](https://mmbiz.qpic.cn/sz_mmbiz_jpg/j2RPloCW20omlwSFrEamANWwaD87gRoibSonENeRNTdtGfGFQt7h4H6lEca31BaQQLSpIXuH1PicSsZw2z3oMib4SHbY7kiaOMU6Bmjot3G5pg8/640?wx_fmt=jpeg&from=appmsg)

![面向领域智能体的强化学习演化树](https://mmbiz.qpic.cn/sz_mmbiz_jpg/j2RPloCW20ryIrKTP0wvx6BXmkiaj5smtZoNOcwrlnXwuykgP9uzvXUCM8l3P4ibicFrQ8Xw0hiaagonzHFpjicoiacibNQ1HUfoMvf2qcQ1OVuHicE/640?wx_fmt=jpeg&from=appmsg)

![基于强化学习的search agent与research agent方法汇总](https://mmbiz.qpic.cn/sz_mmbiz_jpg/j2RPloCW20rRuoc5Dg6GIL92jdFZtOdOLS1UKgYdECnF9kJEgbhHeQiaqMD44g8almrIADHRvLj6YQmH9LAKk0uFUsnfTqD9gRJqX49XKibmg/640?wx_fmt=jpeg&from=appmsg)

![面向代码与软件工程智能体的强化学习方法汇总](https://mmbiz.qpic.cn/sz_mmbiz_jpg/j2RPloCW20rpLFnNcL0RFtHgtvpexrTPqq193olxyuq20XbZuAjiaSicXvy5LYWdPtKFJohTQWhW9hsP7sgy1mCHIvBLKQdejaXzrSuZSzyiaA/640?wx_fmt=jpeg&from=appmsg)

![面向数学推理智能体的强化学习方法汇总](https://mmbiz.qpic.cn/mmbiz_jpg/j2RPloCW20o5iaSIopYQWZHic6lsZhz6K2vG6YzAa8dY3A1d38BYTw0iaicIJEdPj1rwHPsTibiaC6ic1yViaCshKphkfSRp2oTkKAxibtYX2Ekx8uoY/640?wx_fmt=jpeg&from=appmsg)

![按训练范式和环境复杂度分类的 GUI 智能体方法汇总](https://mmbiz.qpic.cn/mmbiz_jpg/j2RPloCW20oA359joI2kVjjflte0d6mXyertbnBRxiaC2dFeB38b7PGeTQRudx71UnamibTLK4iaATwQw9kic4ZGXYaltJ4OWtxbnPGT3ibRvicZI/640?wx_fmt=jpeg&from=appmsg)

![基于 LLM 的多智能体系统中强化学习与演化范式汇总。“Dynamic”表示该多智能体系统是否为任务动态，即是否以不同配置（智能体数量、拓扑结构、推理深度、提示词等）处理不同任务查询。“Train”表示该方法是否对智能体的 LLM 主干进行训练](https://mmbiz.qpic.cn/sz_mmbiz_jpg/j2RPloCW20p60Mfl69lza9HQia8z63vtCuOAuX5GlwGZbibFneVkRZ1RdV98lgrvh5ladY12qg8OuNTZYoyne2icCmYH2S8dNBDYVIvgdvcQsI/640?wx_fmt=jpeg&from=appmsg)

![：面向智能体强化学习的环境与基准概览，按智能体能力、任务领域及模态分类。智能体能力以如下符号表示： 推理、 规划、工具使用、记忆、协作、自我改进](https://mmbiz.qpic.cn/sz_mmbiz_jpg/j2RPloCW20qK5hnGGTQFeAoRiax9GibulECaYgXX6o1fYVGlcr6wzT1CUsGt954XaBicHymN5SeyV2QkQ84ibBZ90dqc4YnTAd37wK9rZ3Z7ZoM/640?wx_fmt=jpeg&from=appmsg)

![按类型与关键特征分类的强化学习框架汇总](https://mmbiz.qpic.cn/mmbiz_jpg/j2RPloCW20qjjbcTtYyq1uqPlFVk3gGZOOH5JTicSbCkeA7LoZG1ICGLuaZW0iaibP39sPaK7fCibwVWXcx8VLHHosb9PGa3hgNShBicMYYPX1QU/640?wx_fmt=jpeg&from=appmsg)

该综述去年发布，梳理了大语言模型（LLM）+ 智能体（Agent）+ 强化学习（RL）交叉领域的全景综述。文章整合了全球 500+ 项最新研究，今年4月又增加了不少新的工作。

## 一、背景

![传统 LLM vs Agentic RL](data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA2MDAgMjUwIj4KICAgICAgICA8ZGVmcz48bWFya2VyIGlkPSJhcnJvdyIgdmlld0JveD0iMCAwIDEwIDEwIiByZWZYPSI4IiByZWZZPSI1IiBtYXJrZXJXaWR0aD0iNiIgbWFya2VySGVpZ2h0PSI2IiBvcmllbnQ9ImF1dG8tc3RhcnQtcmV2ZXJzZSI+PHBhdGggZD0iTSAwIDAgTCAxMCA1IEwgMCAxMCB6IiBmaWxsPSIjMzMzIi8+PC9tYXJrZXI+PC9kZWZzPgogICAgICAgIDwhLS0gQmFja2dyb3VuZCAtLT4KICAgICAgICA8cmVjdCB3aWR0aD0iNjAwIiBoZWlnaHQ9IjI1MCIgZmlsbD0iI2ZkZmJmNyIgcng9IjE1IiBzdHJva2U9IiNkZGQiIHN0cm9rZS13aWR0aD0iMiIvPgogICAgICAgIAogICAgICAgIDwhLS0gTGVmdCBTaWRlOiBMTE0gLS0+CiAgICAgICAgPHJlY3QgeD0iMzAiIHk9IjQwIiB3aWR0aD0iMjQwIiBoZWlnaHQ9IjE3MCIgZmlsbD0iI2UzZjJmZCIgcng9IjEwIiBzdHJva2U9IiM5MGNhZjkiLz4KICAgICAgICA8Y2lyY2xlIGN4PSIxNTAiIGN5PSIxMDAiIHI9IjQwIiBmaWxsPSIjYmJkZWZiIiBzdHJva2U9IiMxZTg4ZTUiIHN0cm9rZS13aWR0aD0iMiIvPgogICAgICAgIDx0ZXh0IHg9IjE1MCIgeT0iMTA1IiBmb250LWZhbWlseT0ic2Fucy1zZXJpZiIgZm9udC1zaXplPSIzMCIgdGV4dC1hbmNob3I9Im1pZGRsZSI+8J+Xo++4jzwvdGV4dD4KICAgICAgICA8dGV4dCB4PSIxNTAiIHk9IjE1MCIgZm9udC1mYW1pbHk9InNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTgiIGZvbnQtd2VpZ2h0PSJib2xkIiBmaWxsPSIjMGQ0N2ExIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj7kvKDnu58gTExNPC90ZXh0PgogICAgICAgIDx0ZXh0IHg9IjE1MCIgeT0iMTgwIiBmb250LWZhbWlseT0ic2Fucy1zZXJpZiIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzMzMyIgdGV4dC1hbmNob3I9Im1pZGRsZSI+5YOP44CM5a2m6Zy444CN77ya5Y+q5oeC5YGa6aKY77yMPC90ZXh0PgogICAgICAgIDx0ZXh0IHg9IjE1MCIgeT0iMjAwIiBmb250LWZhbWlseT0ic2Fucy1zZXJpZiIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzMzMyIgdGV4dC1hbmNob3I9Im1pZGRsZSI+5rKh5pyJ5omL6ISa77yM5LiN6IO96KGM5Yqo44CCPC90ZXh0PgoKICAgICAgICA8IS0tIFJpZ2h0IFNpZGU6IEFnZW50aWMgUkwgLS0+CiAgICAgICAgPHJlY3QgeD0iMzMwIiB5PSI0MCIgd2lkdGg9IjI0MCIgaGVpZ2h0PSIxNzAiIGZpbGw9IiNlOGY1ZTkiIHJ4PSIxMCIgc3Ryb2tlPSIjYTVkNmE3Ii8+CiAgICAgICAgPGNpcmNsZSBjeD0iNDUwIiBjeT0iMTAwIiByPSI0MCIgZmlsbD0iI2M4ZTZjOSIgc3Ryb2tlPSIjNDNhMDQ3IiBzdHJva2Utd2lkdGg9IjIiLz4KICAgICAgICA8dGV4dCB4PSI0NTAiIHk9IjEwNSIgZm9udC1mYW1pbHk9InNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMzAiIHRleHQtYW5jaG9yPSJtaWRkbGUiPvCfpJY8L3RleHQ+CiAgICAgICAgPCEtLSBIYW5kcyAtLT4KICAgICAgICA8cmVjdCB4PSI0MDAiIHk9IjEwMCIgd2lkdGg9IjQwIiBoZWlnaHQ9IjEwIiBmaWxsPSIjNDNhMDQ3IiByeD0iNSIvPgogICAgICAgIDxyZWN0IHg9IjQ2MCIgeT0iMTAwIiB3aWR0aD0iNDAiIGhlaWdodD0iMTAiIGZpbGw9IiM0M2EwNDciIHJ4PSI1Ii8+CiAgICAgICAgPHRleHQgeD0iNDUwIiB5PSIxNTAiIGZvbnQtZmFtaWx5PSJzYW5zLXNlcmlmIiBmb250LXNpemU9IjE4IiBmb250LXdlaWdodD0iYm9sZCIgZmlsbD0iIzFiNWUyMCIgdGV4dC1hbmNob3I9Im1pZGRsZSI+QWdlbnRpYyBSTDwvdGV4dD4KICAgICAgICA8dGV4dCB4PSI0NTAiIHk9IjE4MCIgZm9udC1mYW1pbHk9InNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTQiIGZpbGw9IiMzMzMiIHRleHQtYW5jaG9yPSJtaWRkbGUiPuWDj+OAjOW3peeoi+W4iOOAje+8mjwvdGV4dD4KICAgICAgICA8dGV4dCB4PSI0NTAiIHk9IjIwMCIgZm9udC1mYW1pbHk9InNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTQiIGZpbGw9IiMzMzMiIHRleHQtYW5jaG9yPSJtaWRkbGUiPuiDveaAneiAg+OAgeiDveWKqOaJi+OAgeS8muWPjeaAneOAgjwvdGV4dD4KICAgICAgICAKICAgICAgICA8IS0tIFZTIFRleHQgLS0+CiAgICAgICAgPHRleHQgeD0iMzAwIiB5PSIxMzAiIGZvbnQtZmFtaWx5PSJzYW5zLXNlcmlmIiBmb250LXNpemU9IjI0IiBmb250LXdlaWdodD0iYm9sZCIgZmlsbD0iI2QzMmYyZiIgdGV4dC1hbmNob3I9Im1pZGRsZSI+VlM8L3RleHQ+CiAgICA8L3N2Zz4=)



- 传统 LLM-RL（RLHF/DPO 等）把大模型当作静态、单步、被动的文本生成器，**重点优化输出是否符合偏好，用来对齐用**。
- Agentic RL 把大模型当作动态、连续自主的决策智能体，用强化学习优化**完整交互与决策能力**


## 二、 从 LLM RL 到 Agentic RL 范式演进

![单步 MDP vs 多步 POMDP](data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA2MDAgMjAwIj4KICAgICAgICA8cmVjdCB3aWR0aD0iNjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2ZmZjNlMCIgcng9IjE1IiBzdHJva2U9IiNmZmUwYjIiIHN0cm9rZS13aWR0aD0iMiIvPgogICAgICAgIAogICAgICAgIDwhLS0gTGVmdDogTURQIC0tPgogICAgICAgIDxyZWN0IHg9IjMwIiB5PSIzMCIgd2lkdGg9IjI0MCIgaGVpZ2h0PSIxNDAiIGZpbGw9IiNmZmZmZmYiIHJ4PSI4IiBzdHJva2U9IiNmZmI3NGQiLz4KICAgICAgICA8cGF0aCBkPSJNIDYwIDEwMCBMIDE1MCAxMDAiIHN0cm9rZT0iIzMzMyIgc3Ryb2tlLXdpZHRoPSIzIiBtYXJrZXItZW5kPSJ1cmwoI2Fycm93KSIvPgogICAgICAgIDxjaXJjbGUgY3g9IjYwIiBjeT0iMTAwIiByPSIxNSIgZmlsbD0iI2ZmY2M4MCIvPgogICAgICAgIDxjaXJjbGUgY3g9IjE1MCIgY3k9IjEwMCIgcj0iMTUiIGZpbGw9IiNmZmNjODAiLz4KICAgICAgICA8dGV4dCB4PSIxNTAiIHk9IjE0MCIgZm9udC1mYW1pbHk9InNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTYiIGZvbnQtd2VpZ2h0PSJib2xkIiBmaWxsPSIjZTY1MTAwIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj5NRFAgKOWNleatpSk8L3RleHQ+CiAgICAgICAgPHRleHQgeD0iMTUwIiB5PSIxNjAiIGZvbnQtZmFtaWx5PSJzYW5zLXNlcmlmIiBmb250LXNpemU9IjE0IiBmaWxsPSIjNTU1IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj7kuIDnnLznnIvliLDlupU8L3RleHQ+CiAgICAgICAgPHRleHQgeD0iMTUwIiB5PSIxNzUiIGZvbnQtZmFtaWx5PSJzYW5zLXNlcmlmIiBmb250LXNpemU9IjE0IiBmaWxsPSIjNTU1IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj7kuIDmrKHnlJ/miJDlrow8L3RleHQ+CgogICAgICAgIDwhLS0gUmlnaHQ6IFBPTURQIC0tPgogICAgICAgIDxyZWN0IHg9IjMzMCIgeT0iMzAiIHdpZHRoPSIyNDAiIGhlaWdodD0iMTQwIiBmaWxsPSIjZmZmZmZmIiByeD0iOCIgc3Ryb2tlPSIjODFjNzg0Ii8+CiAgICAgICAgPHBhdGggZD0iTSAzNjAgMTAwIEwgNDAwIDgwIEwgNDQwIDEyMCBMIDQ4MCAxMDAgTCA1MjAgMTAwIiBzdHJva2U9IiMzMzMiIHN0cm9rZS13aWR0aD0iMyIgZmlsbD0ibm9uZSIgbWFya2VyLWVuZD0idXJsKCNhcnJvdykiLz4KICAgICAgICA8IS0tIEZvZyBjbG91ZHMgLS0+CiAgICAgICAgPGNpcmNsZSBjeD0iNDIwIiBjeT0iNjAiIHI9IjE1IiBmaWxsPSIjZTBlMGUwIiBvcGFjaXR5PSIwLjUiLz4KICAgICAgICA8Y2lyY2xlIGN4PSI0NjAiIGN5PSIxNDAiIHI9IjE1IiBmaWxsPSIjZTBlMGUwIiBvcGFjaXR5PSIwLjUiLz4KICAgICAgICA8dGV4dCB4PSI0NTAiIHk9IjE0MCIgZm9udC1mYW1pbHk9InNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTYiIGZvbnQtd2VpZ2h0PSJib2xkIiBmaWxsPSIjMmU3ZDMyIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj5QT01EUCAo5aSa5q2lKTwvdGV4dD4KICAgICAgICA8dGV4dCB4PSI0NTAiIHk9IjE2MCIgZm9udC1mYW1pbHk9InNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTQiIGZpbGw9IiM1NTUiIHRleHQtYW5jaG9yPSJtaWRkbGUiPui1sOS4gOatpeeci+S4gOatpTwvdGV4dD4KICAgICAgICA8dGV4dCB4PSI0NTAiIHk9IjE3NSIgZm9udC1mYW1pbHk9InNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTQiIGZpbGw9IiM1NTUiIHRleHQtYW5jaG9yPSJtaWRkbGUiPui+ueWBmui+ueiwg+aVtDwvdGV4dD4KCiAgICAgICAgPGRlZnM+CiAgICAgICAgICAgIDxtYXJrZXIgaWQ9ImFycm93IiB2aWV3Qm94PSIwIDAgMTAgMTAiIHJlZlg9IjEwIiByZWZZPSI1IiBtYXJrZXJXaWR0aD0iNiIgbWFya2VySGVpZ2h0PSI2IiBvcmllbnQ9ImF1dG8tc3RhcnQtcmV2ZXJzZSI+CiAgICAgICAgICAgICAgPHBhdGggZD0iTSAwIDAgTCAxMCA1IEwgMCAxMCB6IiBmaWxsPSIjMzMzIiAvPgogICAgICAgICAgICA8L21hcmtlcj4KICAgICAgICA8L2RlZnM+CiAgICA8L3N2Zz4=)



综述在理论上的最大贡献，是将大模型对齐的底层数学模型，从**马尔可夫决策过程（MDP）**演进至**时序扩展的部分可观测马尔可夫决策过程（POMDP）。从而来说明LLM RL到Agentic RL的演进过程。
从 LLM RL 到 Agentic RL 的范式转变。扇形设计体现了 RL 表述的向外扩展——从传统 RL（内层），到 LLM RL，再到完整的 Agentic RL（外层）。颜色编码区域表示：红色 = LLM RL 特有功能；蓝绿色 = AgenticRL 所需功能；紫色 = 现有 Agentic RL 实现。箭头向外指，表示在迈向更具智能体特性的设置时，交互广度（工具使用、网页浏览、动态环境）不断增加

### 2.1传统偏好强化学习（PBRFT / RLHF）：单步MDP范式

传统RLHF可以建模为一个**单步马尔可夫决策过程（Single-step MDP）**，其形式定义为：

- **状态空间**：仅包含由用户初始提示（prompt）定义的单一静态状态，整个交互过程中状态不发生变化。
- **动作空间**：模型的唯一动作是生成一段完整的文本序列。
- **转移动态**：模型生成回应后，交互过程立即终止，时间跨度固定为，属于典型的单步决策问题。
- **奖励函数**：奖励是对整段生成文本的一次性标量评估，通常由预先训练好的奖励模型给出，仅在对话结束时提供一次反馈。
- **学习目标**：优化目标为最大化单步期望奖励：

> PBRFT的逻辑就像做一道“一次性选择题”：给定题干（prompt），**模型直接输出完整答案（生成文本），随后获得一个最终分数（reward），整个过程只有一步决策**。

### 2.2智能体强化学习（Agentic RL）：长程POMDP范式

Agentic RL的场景复杂度显著提升，需建模为**部分可观测马尔可夫决策过程（POMDP）**，其形式定义为：

- **状态空间**与观测模型：环境状态随交互动态演化，且智能体无法直接观测完整状态，只能通过观测模型获取部分信息，属于典型的“部分可观测”场景。
- **动作空间**：采用混合式动作空间，覆盖文本与工具交互两类行为：
- **转移动态**：环境根据智能体的动作随机转移到下一状态，时间跨度，支持多步长时序交互。
- **奖励函数**：采用分层奖励设计，既包含任务完成时的稀疏终局奖励，也包含基于中间步骤进度的稠密反馈奖励，解决长程任务的信用分配难题。
- **学习目标**：优化目标为最大化长程折扣累积奖励，引导模型兼顾短期行为有效性与长期任务目标：

### 2.3传统 PBRFT（RLHF/DPO）和Agentic RL详细对比

维度
传统 PBRFT（RLHF/DPO）
Agentic RL
决策过程
退化单步 MDP
时序扩展 POMDP
观测
完全可观测
部分可观测
动作
仅文本生成
文本 + 工具 / 环境操作
奖励
单步最终奖励
稠密步骤奖励 + 最终奖励
优化目标
定位
被动生成文本
自主决策智能体

## 三、 主流算法体系

为实现上述 POMDP 目标的求解，当前 Agentic RL 演化出三大主流算法谱系：

### 1. PPO 系列

- **机制**：通过 Actor-Critic 架构进行在线策略梯度更新，是目前最通用的对齐算法（衍生如 VinePPO, LitePPO）。
- **目标函数**：其中优势函数。

### 2. DPO 系列

- **机制**：将强化学习问题转化为监督学习中的分类问题，无需训练独立的奖励模型（RM），简单高效（衍生如 SimPO, IPO, Step-DPO）。
- **目标函数**：

### 3. GRPO 系列

![GRPO 原理图解](data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA2MDAgMzAwIj4KICAgICAgICA8cmVjdCB3aWR0aD0iNjAwIiBoZWlnaHQ9IjMwMCIgZmlsbD0iI2YzZTVmNSIgcng9IjE1IiBzdHJva2U9IiNjZTkzZDgiIHN0cm9rZS13aWR0aD0iMiIvPgogICAgICAgIDx0ZXh0IHg9IjMwMCIgeT0iNDAiIGZvbnQtZmFtaWx5PSJzYW5zLXNlcmlmIiBmb250LXNpemU9IjIwIiBmb250LXdlaWdodD0iYm9sZCIgZmlsbD0iIzRhMTQ4YyIgdGV4dC1hbmNob3I9Im1pZGRsZSI+R1JQTyDljp/nkIbvvJrlsI/nu4TlhoXljbfvvIzkvJjog5zliqPmsbA8L3RleHQ+CiAgICAgICAgCiAgICAgICAgPCEtLSBTdHVkZW50cyAtLT4KICAgICAgICA8IS0tIFN0dWRlbnQgQSAtLT4KICAgICAgICA8cmVjdCB4PSI1MCIgeT0iNzAiIHdpZHRoPSIxMDAiIGhlaWdodD0iMTIwIiBmaWxsPSIjZmZmZmZmIiByeD0iNSIgc3Ryb2tlPSIjYWI0N2JjIi8+CiAgICAgICAgPHRleHQgeD0iMTAwIiB5PSIxMDAiIGZvbnQtZmFtaWx5PSJzYW5zLXNlcmlmIiBmb250LXNpemU9IjI0IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj7wn5Go4oCN8J+OkzwvdGV4dD4KICAgICAgICA8dGV4dCB4PSIxMDAiIHk9IjE0MCIgZm9udC1mYW1pbHk9InNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTYiIGZvbnQtd2VpZ2h0PSJib2xkIiBmaWxsPSIjMzMzIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj7lrabnlJ8gQTwvdGV4dD4KICAgICAgICA8dGV4dCB4PSIxMDAiIHk9IjE3MCIgZm9udC1mYW1pbHk9InNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMjAiIGZpbGw9IiMyZTdkMzIiIHRleHQtYW5jaG9yPSJtaWRkbGUiPuW+l+WIhjogOTA8L3RleHQ+CiAgICAgICAgCiAgICAgICAgPCEtLSBTdHVkZW50IEIgLS0+CiAgICAgICAgPHJlY3QgeD0iMjAwIiB5PSI3MCIgd2lkdGg9IjEwMCIgaGVpZ2h0PSIxMjAiIGZpbGw9IiNmZmZmZmYiIHJ4PSI1IiBzdHJva2U9IiNhYjQ3YmMiLz4KICAgICAgICA8dGV4dCB4PSIyNTAiIHk9IjEwMCIgZm9udC1mYW1pbHk9InNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMjQiIHRleHQtYW5jaG9yPSJtaWRkbGUiPvCfkanigI3wn46TPC90ZXh0PgogICAgICAgIDx0ZXh0IHg9IjI1MCIgeT0iMTQwIiBmb250LWZhbWlseT0ic2Fucy1zZXJpZiIgZm9udC1zaXplPSIxNiIgZm9udC13ZWlnaHQ9ImJvbGQiIGZpbGw9IiMzMzMiIHRleHQtYW5jaG9yPSJtaWRkbGUiPuWtpueUnyBCPC90ZXh0PgogICAgICAgIDx0ZXh0IHg9IjI1MCIgeT0iMTcwIiBmb250LWZhbWlseT0ic2Fucy1zZXJpZiIgZm9udC1zaXplPSIyMCIgZmlsbD0iI2M2MjgyOCIgdGV4dC1hbmNob3I9Im1pZGRsZSI+5b6X5YiGOiA0MDwvdGV4dD4KCiAgICAgICAgPCEtLSBTdHVkZW50IEMgLS0+CiAgICAgICAgPHJlY3QgeD0iMzUwIiB5PSI3MCIgd2lkdGg9IjEwMCIgaGVpZ2h0PSIxMjAiIGZpbGw9IiNmZmZmZmYiIHJ4PSI1IiBzdHJva2U9IiNhYjQ3YmMiLz4KICAgICAgICA8dGV4dCB4PSI0MDAiIHk9IjEwMCIgZm9udC1mYW1pbHk9InNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMjQiIHRleHQtYW5jaG9yPSJtaWRkbGUiPvCfp5HigI3wn46TPC90ZXh0PgogICAgICAgIDx0ZXh0IHg9IjQwMCIgeT0iMTQwIiBmb250LWZhbWlseT0ic2Fucy1zZXJpZiIgZm9udC1zaXplPSIxNiIgZm9udC13ZWlnaHQ9ImJvbGQiIGZpbGw9IiMzMzMiIHRleHQtYW5jaG9yPSJtaWRkbGUiPuWtpueUnyBDPC90ZXh0PgogICAgICAgIDx0ZXh0IHg9IjQwMCIgeT0iMTcwIiBmb250LWZhbWlseT0ic2Fucy1zZXJpZiIgZm9udC1zaXplPSIyMCIgZmlsbD0iI2Y1N2YxNyIgdGV4dC1hbmNob3I9Im1pZGRsZSI+5b6X5YiGOiA2MDwvdGV4dD4KICAgICAgICAKICAgICAgICA8IS0tIEF2ZXJhZ2UgTGluZSAtLT4KICAgICAgICA8bGluZSB4MT0iNTAiIHkxPSIyMjAiIHgyPSI1NTAiIHkyPSIyMjAiIHN0cm9rZT0iIzZhMWI5YSIgc3Ryb2tlLXdpZHRoPSIzIiBzdHJva2UtZGFzaGFycmF5PSIxMCw1Ii8+CiAgICAgICAgPHRleHQgeD0iNTYwIiB5PSIyMjUiIGZvbnQtZmFtaWx5PSJzYW5zLXNlcmlmIiBmb250LXNpemU9IjE0IiBmaWxsPSIjNmExYjlhIj7lubPlnYfliIYgNjM8L3RleHQ+CiAgICAgICAgCiAgICAgICAgPCEtLSBSZXdhcmRzIC0tPgogICAgICAgIDxwYXRoIGQ9Ik0gMTAwIDE5MCBMIDEwMCAyNTAiIHN0cm9rZT0iIzJlN2QzMiIgc3Ryb2tlLXdpZHRoPSIyIiBtYXJrZXItZW5kPSJ1cmwoI2Fycm93MikiLz4KICAgICAgICA8dGV4dCB4PSIxMDAiIHk9IjI3MCIgZm9udC1mYW1pbHk9InNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTYiIGZvbnQtd2VpZ2h0PSJib2xkIiBmaWxsPSIjMmU3ZDMyIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj7wn42sIOWlluWKsSAoKyk8L3RleHQ+CiAgICAgICAgCiAgICAgICAgPHBhdGggZD0iTSAyNTAgMTkwIEwgMjUwIDI1MCIgc3Ryb2tlPSIjYzYyODI4IiBzdHJva2Utd2lkdGg9IjIiIG1hcmtlci1lbmQ9InVybCgjYXJyb3cyKSIvPgogICAgICAgIDx0ZXh0IHg9IjI1MCIgeT0iMjcwIiBmb250LWZhbWlseT0ic2Fucy1zZXJpZiIgZm9udC1zaXplPSIxNiIgZm9udC13ZWlnaHQ9ImJvbGQiIGZpbGw9IiNjNjI4MjgiIHRleHQtYW5jaG9yPSJtaWRkbGUiPvCfkY4g5oOp572aICgtKTwvdGV4dD4KCiAgICAgICAgPGRlZnM+CiAgICAgICAgICAgIDxtYXJrZXIgaWQ9ImFycm93MiIgdmlld0JveD0iMCAwIDEwIDEwIiByZWZYPSIxMCIgcmVmWT0iNSIgbWFya2VyV2lkdGg9IjYiIG1hcmtlckhlaWdodD0iNiIgb3JpZW50PSJhdXRvLXN0YXJ0LXJldmVyc2UiPgogICAgICAgICAgICAgIDxwYXRoIGQ9Ik0gMCAwIEwgMTAgNSBMIDAgMTAgeiIgLz4KICAgICAgICAgICAgPC9tYXJrZXI+CiAgICAgICAgPC9kZWZzPgogICAgPC9zdmc+)



- **机制**：**放弃了传统 PPO 中与 Actor 同等规模的 Critic（价值网络）**。针对同一个输入 Prompt（问题），模型一次性采样个不同的输出轨迹（组），通过计算这组轨迹的相对得分来更新策略。**极大地节省了显存（少加载一个千亿参数模型），是当前大模型 RL（如 DeepSeek-R1）的绝对主流**。
- **目标函数**： GRPO 的目标是最大化以下目标函数

PPO、DPO 与 GRPO 系列主流变体的对比。Clip 指将策略比值限制在 1 附近，防止其变动过大，从而保证更新稳定；KLpenalty 指对学习策略与参考策略之间的 KL 散度施加惩罚，以确保对齐

# 四、RL 赋能的六大智能体能力

### LLM Agent–环境交互与 RL 循环

面向智能体 LLM 的智能体–环境交互与 RL 循环。核心智能体能力驱动动作生成，环境提供反馈与奖励，这些通过基于 RL 的优化在多样化任务域中聚合（“Collab.”表示需要显式任务划分与多智能体协调的任务）

### 1.规划（Planning）

规划是智能体为达成长期目标，对未来动作、推理步骤、工具调用序列进行预结构化与序贯决策的能力，是智能体从“被动响应”走向“主动控制”的核心标志。

#### 强化学习的核心作用

RL 将规划从**固定提示、静态分解、无反馈**升级为**可学习、可自适应、可随环境优化的策略**，解决传统方法无法适应动态环境、无法从失败中修正规划的问题。

#### 两大范式

**（1）RL 作为外部引导（External Guide）**

- 机制：不直接微调LLM参数，而是训练**价值网络/启发式函数**，指导MCTS等搜索算法选择高价值规划路径。

> 核心逻辑：LLM负责生成候选动作，RL负责评估与引导搜索。

- 典型工作：
- 优势：不破坏LLM原有生成能力，即插即用。

**（2）RL 作为内部驱动（Internal Driver）**

- 机制：直接将LLM视为策略网络，通过与环境交互**端到端微调**，让规划能力内化为模型行为。

> 核心逻辑：规划不再是单纯的prompt，而是LLM在交互中习得的内在策略。

- 典型工作：
- 优势：完全自主、动态适应、可长期自我改进。

#### 结论

- 传统规划：固定prompt分解、无反馈、不可学习。
- Agentic RL 规划：**价值引导+策略学习**，实现动态、自适应、长程、鲁棒的序贯决策。

### 2.工具使用（Tool Using）

工具使用是智能体在推理过程中自主调用外部模块（检索、计算器、浏览器、代码解释器、API等）扩展能力的行为，是LLM突破知识边界的关键。
智能体工具使用的发展

#### 强化学习的核心作用

RL让工具使用从**模仿、固定模式、不可泛化**升级为**战略级自主决策**，实现“何时用、用什么、如何组合、如何从错误恢复”。

#### 三阶段演进

**（1）早期：ReAct 式提示范式（无RL）**

- 代表：ReAct
- 模式：Think → Act → Observe

> 局限：纯上下文学习、不可学习、无法泛化新工具。

**（2）中期：监督微调 SFT（无RL）**

- 代表：Toolformer、AgentTuning、FireAct
- 模式：学习固定工具调用格式

> 局限：静态复制、无法处理异常、不会动态决策。

**（3）高阶：RL 驱动工具集成推理 TIR（Agentic RL 核心）**

- 定义：Tool-integrated Reasoning，工具调用与认知推理深度融合。
- RL 机制：
- 典型工作：
- 优势：自适应、鲁棒、可处理复杂多工具协同。

#### 区别

- **传统工具使用**：模仿学习、静态格式、被动触发。
- **Agentic RL 工具使用**：**自主策略、动态调度、长程规划、错误恢复**，真正实现工具增强智能。

## 3.记忆（Memory）

记忆是智能体**对历史信息、对话、知识、经验进行存储、检索、更新、遗忘与管理的能力，是长时程交互的基础**。
三类经典智能体Memory方案

#### 强化学习的核心作用

RL让记忆从**被动存储、固定规则、启发式检索**升级为**可学习、可控制、可优化的主动管理系统**。

#### 三大技术路线

**1.RAG 风格记忆 + RL**

- 机制：RL控制**检索时机、写入策略、摘要粒度、重排排序**。
- 代表：Memory-R1、Prospect、Mem-α
- 能力：学习何时查、查什么、如何整合记忆。

**2.Token 级记忆 + RL**

- 显式记忆Token：MemAgent、MEM1、Memory Token
- 隐式记忆Token：MemoryLLM、M+、MemGen

**3.结构化记忆 + RL（前沿方向）**

- 形态：时序知识图谱、层级图、原子记忆单元
- 代表：Zep、G-Memory、A-MEM、Mem0
- 未来方向：RL自动控制图谱增删改查（尚未充分探索）。

#### 对比

- **传统记忆：静态存储、规则检索、无自适应。**

- **Agentic RL 记忆**：**RL驱动全生命周期管理**，**包括写入、检索、更新、遗忘、压缩、扩展**。

### 4.自我改进（Self-Improving）

> 智能体通过反思、纠错、迭代、自博弈、自训练，持续提升自身策略、推理与规划的能力，是通用智能的核心标志。

#### 强化学习的核心作用

RL让自我改进从**一次性语言反思**升级为**可固化、可迭代、可无限进化**的内在能力。

#### 三层进化体系

**（1）语言自我纠正（非参数、无梯度）**

- 机制：生成→评判→改写，纯文本反馈。
- 代表：Reflexion、Self-Refine、CRITIC、Chain-of-Verification
- 局限：改进不持久、不内化到参数。

**（2）内化自我纠正（参数化 RL）**

- 机制：用DPO/GRPO/RPO将反思能力固化到模型权重。
- 代表：Reflection-DPO、KnowSelf、DuPo
- 优势：反思成为模型固有行为，跨任务泛化。

**（3）迭代自我训练（最高阶、无上限进化）**

- 机制：自创任务、自博弈、自验证、RL迭代。
- 代表：
- 优势：完全自主、脱离数据、无限进化。

#### 结论

- **传统自我改进：临时纠错、不可迁移。**
- Agentic RL 自我改进：**反思→参数固化→自博弈迭代**，**实现真正自主智能体进化。**

### 5.推理（Reasoning）

> 推理是智能体对问题进行逻辑推断、多步演绎、验证与反思的能力，综述采用双系统理论：快思考 vs 慢思考。

#### 强化学习的核心作用

RL解决**快思考易幻觉、慢思考效率低**的问题，实现**自适应思考长度**，并激励严谨、可信、长程推理。

#### 双系统 + RL

**（1）快推理（System 1）**

- 直觉、快速、一步到位
- 缺陷：易幻觉、浅推理
- RL作用：学习置信度、拒绝不确定问题。

**（2）慢推理（System 2）**

- 多步、结构化、验证式、长思维链
- RL作用：
- 代表：DeepSeek-R1、OpenAI o1/o3、GRPO、Reflexion

#### Agentic RL 推理创新

- 自适应思考：根据难度自动选择快慢思考。
- 过程奖励：解决长推理信用分配难题。
- 可验证奖励：基于执行/符号检验降低幻觉。

#### 结论

- **传统推理：固定长度、单步生成、不可控**。
- **Agentic RL 推理**：**快慢协同、自适应思考、过程监督、自我修正**。

### 6.感知（Perception）

> 感知是智能体获取并理解多模态信息（图像、视频、音频、状态）的能力，从“被动看图”升级为“主动视觉认知”。

#### 强化学习的核心作用

RL让感知从**被动特征提取**升级为**主动感知、交互式查询、聚焦式理解**。

#### 三大主动感知范式

**（1）定位驱动感知**

- 机制：推理步骤绑定图像区域，反复查询、聚焦、验证。
- 代表：GRIT、Ground-R1、DeepEyes、Chain-of-Focus
- 能力：看哪里、聚焦哪里、回看哪里。

**（2）工具驱动感知**

- 机制：调用视觉工具（检测、分割、编辑、绘制）辅助认知。
- 代表：VisTA、VTool-R1、Visual-ARFT、Pixel-Reasoner
- 能力：用工具“增强眼睛”。

**（3）生成驱动感知**

- 机制：在推理中生成草图、想象图像，辅助逻辑推理。
- 代表：Visual Planning、GoT-R1、T2I-R1
- 能力：用想象力辅助感知与推理。

#### 多模态扩展

- 视觉：Vision-R1、VLM-R1、Visual-RFT
- 音频：RL优化TTS与音频问答
- 3D感知：3D空间推理与RL奖励塑形

#### 结论

- 传统感知：被动输入、一次性编码、无交互。
- Agentic RL 感知：**主动看、聚焦看、反复看、用工具看、用想象看**。

RL 如何在六大核心能力上赋能智能体 LLM 的概览。中央面板汇总能力分类，侧面板展示代表性 RL 机制与交互模式。
能力
传统方式（无RL）
Agentic RL 方式
核心升级
规划
固定Prompt分解
外部价值引导 + 内部策略学习
动态自适应、长程鲁棒
工具使用
ReAct/SFT静态模仿
工具集成推理TIR、自主策略
战略调用、错误恢复
记忆
规则检索、被动存储
RL全生命周期主动管理
读写优化、自适应遗忘
自我改进
临时语言反思
内化纠错 + 自博弈迭代
永久进化、无上限
推理
固定长度单步生成
快慢双系统 + 自适应思考
低幻觉、强严谨
感知
被动看图
主动定位+工具+想象
交互式、多步认知

## 五、应用领域

Agentic RL 已落地高验证性、高交互性任务：

- search / deep research agent：**自主联网检索、深度报告**（OpenAI Deep Research、Search-R1）；
- 代码智能体：生成、调试、软件工程（SWE-Bench、DeepSWE、Qwen3-Coder）；
- 数学智能体：非形式推理 + 形式定理证明（DeepSeek-Prover、rStar2-Agent）；
- GUI 智能体：手机 / 电脑 / 网页自动操作（WebArena、OSWorld、UI-R1）；
- 视觉智能体：多模态主动感知与推理；
- 具身智能体：机器人导航与操控（Voyager）；
- 多智能体系统：协作 / 博弈 / 分工（MAGRPO、MAPoRL）；
- 其他：文本游戏、时序预测、Text-to-SQ

面向领域智能体的强化学习演化树
基于强化学习的search agent与research agent方法汇总
面向代码与软件工程智能体的强化学习方法汇总
面向数学推理智能体的强化学习方法汇总
按训练范式和环境复杂度分类的 GUI 智能体方法汇总
基于 LLM 的多智能体系统中强化学习与演化范式汇总。“Dynamic”表示该多智能体系统是否为任务动态，即是否以不同配置（智能体数量、拓扑结构、推理深度、提示词等）处理不同任务查询。“Train”表示该方法是否对智能体的 LLM 主干进行训练
：面向智能体强化学习的环境与基准概览，按智能体能力、任务领域及模态分类。智能体能力以如下符号表示： 推理、 规划、工具使用、记忆、协作、自我改进
按类型与关键特征分类的强化学习框架汇总

## 六、 核心结论、挑战与未来方向

### 1. 主要发现

- **Scaling 规律**：加大 RL 训练阶段的计算量（Test-time Compute / RL Scaling Law），可系统性提升智能体能力。**充分 RL 训练的小模型可匹敌大模型**。
- **奖励的关键性**：纯 RL 的后训练可能损害事实性，而将 SFT 与可验证奖励的 RL 过程相结合的结构化方法，则可缓解这种退化。**可验证、密集 过程奖励”（Process-based rewards）如 FSPO，对智能体的每一步推理进行事实性验证，从而直接惩罚不真实的中间步骤。这类的的奖励设计是 Agentic RL 成功的关键因素**。

### 2. 当前核心挑战

- **可信度危机**：RL 容易引发Reward Hacking、幻觉放大以及Sycophancy行为(**LLM在有ground truth的情况下，为迎合用户显性表达的信念而偏离事实的行为**)。
- **规模化瓶颈**：长序列多步采样的计算成本极高；模型在强化学习过程中容易出现**熵坍缩（Entropy Collapse)：策略（Policy）的熵值（Entropy）急剧下降，导致策略的随机性显著降低，智能体过早放弃探索，陷入局部最优**
- **环境局限**：当前多为静态模拟器，缺乏能与智能体协同进化的动态自适应训练环境。

### 3. 未来研究方向

1. **可信智能体**：内嵌安全护栏、基于事实的奖励模型设计。
2. **高效训练算法**：低算力消耗、小数据依赖、跨任务迁移的轻量级 RL 算法。
3. **元学习（Meta-Learning）**：让智能体在 RL 过程中学会“如何学习”与“如何反思”。
4. **真实世界部署**：建立“Human-in-the-loop”、分层编排与标准化的多智能体通信协议。

论文：The Landscape of Agentic Reinforcement Learning for LLMs: A Survey
链接：https://arxiv.org/pdf/2509.02547
---

## 📘 特别篇：用 Hermes Agent 秒懂什么是 Agentic RL

为了让你彻底理解，我们不用学术定义，直接拿你熟悉的 **Hermes Agent** 来举例。

### 1. 先拆解概念：什么是 Agentic？什么是 RL？

- **Agentic (智能体)**：指的是 AI 不再只是"嘴炮型"聊天机器人，而是有了"手和脚"。它能调用工具（比如 `terminal` 敲代码、`browser` 爬网页、`skill` 读文档），能自主规划多步任务。
- **RL (强化学习)**：一种"奖罚分明"的训练方式。做对了给奖励（加分），做错了给惩罚（扣分），让模型自己去试错进化，而不是人类手把手教。

### 2. 配合 Hermes Agent 的通俗解释

想象你给 Hermes Agent 下达一个指令：**"帮我修复 NanoHermes 项目里的一个 Bug。"**

**🚫 阶段一：普通大模型（Pre-trained LLM）**
- **行为**：它只能凭记忆里的知识猜测代码怎么改，直接给你一段代码。
- **缺点**：它没运行过你的项目，不知道改完后能不能跑通，经常"瞎编"。

**🔧 阶段二：基础智能体（Basic Agent / SFT）**
- **行为**：Hermes Agent 学会了用工具。它会去 `terminal` 运行 `cat bug.py` 看代码，然后修改，再跑一下测试。
- **缺点**：它的行为是写死的（Hard-coded）或者模仿人类简单操作的。如果报错了，它可能只会复读错误信息，不知道下一步该去查文档还是去搜 Google，遇到复杂 Bug 容易"卡死"或陷入无限循环。

**🚀 阶段三：Agentic RL（智能体强化学习）**
- **行为**：Hermes Agent 经历了成千上万次"做任务 - 拿奖励/受罚"的训练，进化出了**直觉**。
- **具体过程**：
    1. **读取代码**：调用 `read_file`。✅ **奖励+1**（获取了信息）。
    2. **尝试运行**：调用 `terminal` 跑测试，结果报错了。
    3. **自我反思**：它没有傻愣着，而是根据错误信息，判断出需要查文档。
    4. **调用搜索**：使用 `search_files` 或 `browser` 搜解决方案。✅ **奖励+2**（主动利用外部知识）。
    5. **修复代码**：修改代码后再次运行 `terminal`。
    6. **验证成功**：测试通过！🎉 **超级奖励+100**。
    7. **如果失败**：测试没通过。📉 **惩罚-10**（它下次就知道刚才那招不行）。
    8. **如果死循环**：比如它在一个无用的命令上反复执行了 10 次。💣 **严重惩罚-50**（它学会了"及时止损"，不会浪费 Token）。

### 3. 核心区别总结表

| 维度 | 普通大模型 (LLM) | 基础智能体 (Agent) | **Agentic RL (本文主角)** |
| :--- | :--- | :--- | :--- |
| **能力** | 只能说话 | 能说话 + 能用工具 | **能说话 + 自主决策如何用工具 + 能反思** |
| **遇到报错** | 假装没看见 / 瞎猜 | 卡住 / 机械重试 | **分析报错 -> 搜索/查文档 -> 换个策略** |
| **训练方式** | 读书 (海量数据) | 模仿人类操作 (SFT) | **在实战中"奖罚分明"地自我进化** |
| **Hermes 表现** | 给你一个代码片段 | 帮你运行代码，但遇到深层 Bug 可能晕 | **像个熟练工程师，自主 Debug 直到绿灯** |

**一句话总结：**
Agentic RL 就是给拥有"手脚"（工具/环境交互能力）的 Hermes Agent 装上了一个**"进化大脑"**，通过实战中的奖惩反馈，让它在复杂任务中知道**"什么时候该搜、什么时候该写代码、什么时候该停下来反思"**，最终实现从"玩具"到"干活主力"的跨越。

---

## 📘 深度解析：VeRL 中的 Agentic RL 训练全流程（含源码级解读）

为了让你真正理解 Agentic RL 是怎么“跑”起来的，我们深入到 `verl` 的源码层面，把**一条 Trajectory 从生成到梯度更新**的全过程拆开揉碎。

整个过程分为四大核心步骤：
1. **Agent Loop 生成轨迹**（多轮交互）
2. **计算奖励 (Reward)**（环境反馈）
3. **计算优势 (Advantage)**（GRPO/PPO 核心）
4. **计算 Loss 与更新**（策略优化）

---

### 🔄 步骤 1：Agent Loop 生成轨迹

这是 Agent 与环境的“实战”过程。

**核心代码位置**：`verl/experimental/agent_loop/tool_agent_loop.py`

```python
# 状态机循环：生成 -> 工具 -> 再生成 -> ...
state = AgentState.PENDING
while state != AgentState.TERMINATED:
    if state == AgentState.GENERATING:
        # LLM 生成文本，遇到 

---

## 📘 深度解析：VeRL 中的 Agentic RL 训练全流程（含源码级解读）

为了让你真正理解 Agentic RL 是怎么“跑”起来的，我们深入到 `verl` 的源码层面，把**一条 Trajectory 从生成到梯度更新**的全过程拆开揉碎。

整个过程分为四大核心步骤：
1. **Agent Loop 生成轨迹**（多轮交互）
2. **计算奖励 (Reward)**（环境反馈）
3. **计算优势 (Advantage)**（GRPO/PPO 核心）
4. **计算 Loss 与更新**（策略优化）

---

### 🔄 步骤 1：Agent Loop 生成轨迹

这是 Agent 与环境的“实战”过程。

**核心代码位置**：`verl/experimental/agent_loop/tool_agent_loop.py`

```python
# 状态机循环：生成 -> 工具 -> 再生成 -> ...
state = AgentState.PENDING
while state != AgentState.TERMINATED:
    if state == AgentState.GENERATING:
        # LLM 生成文本，遇到         # 遇到 tool call 会暂停生成，解析参数，调用外部工具，拿到结果后塞回上下文继续生成。
        
        # 这里会调用 LLM Server 生成回复
        output = await self.server_manager.generate(...)
        
        # 检查是否生成了 tool call
        _, agent_data.tool_calls = await self.tool_parser.extract_tool_calls(...)
        if agent_data.tool_calls:
            state = AgentState.PROCESSING_TOOLS
        else:
            state = AgentState.TERMINATED # 没工具调用，说明任务完成或无法继续
```

**关键实现细节：**
1.  **Stop Tokens 注入**：在生成前，VeRL 会自动注入 `tool_call` 的 stop tokens（如 `
![Agentic RL 闭环流程](data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8cmVjdCB4PSIxMCIgeT0iMTAiIHdpZHRoPSI1ODAiIGhlaWdodD0iMTgwIiBmaWxsPSIjZjBmOGZmIiBzdHJva2U9IiM0NjgyYjQiIHN0cm9rZS13aWR0aD0iMyIgcng9IjEwIi8+CiAgPHJlY3QgeD0iNTAiIHk9IjgwIiB3aWR0aD0iMTIwIiBoZWlnaHQ9IjQwIiBmaWxsPSIjZDRlZGRhIiBzdHJva2U9ImJsYWNrIiBzdHJva2Utd2lkdGg9IjIiIHJ4PSI1Ii8+CiAgPHRleHQgeD0iMTEwIiB5PSIxMDUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iYmxhY2siIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtd2VpZ2h0PSJib2xkIj5Vc2VyIFByb21wdDwvdGV4dD4KICAKICA8bGluZSB4MT0iMTcwIiB5MT0iMTAwIiB4Mj0iMjIwIiB5Mj0iMTAwIiBzdHJva2U9ImJsYWNrIiBzdHJva2Utd2lkdGg9IjIiIG1hcmtlci1lbmQ9InVybCgjYXJyb3cpIi8+CiAgCiAgPHJlY3QgeD0iMjMwIiB5PSI4MCIgd2lkdGg9IjEyMCIgaGVpZ2h0PSI0MCIgZmlsbD0iI2ZmZjNjZCIgc3Ryb2tlPSJibGFjayIgc3Ryb2tlLXdpZHRoPSIyIiByeD0iNSIvPgogIDx0ZXh0IHg9IjI5MCIgeT0iMTA1IiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTQiIGZpbGw9ImJsYWNrIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXdlaWdodD0iYm9sZCI+TExNIChBY3Rvcik8L3RleHQ+CiAgCiAgPGxpbmUgeDE9IjM1MCIgeTE9IjEwMCIgeDI9IjQwMCIgeTI9IjEwMCIgc3Ryb2tlPSJibGFjayIgc3Ryb2tlLXdpZHRoPSIyIiBtYXJrZXItZW5kPSJ1cmwoI2Fycm93KSIvPgogIAogIDxyZWN0IHg9IjQxMCIgeT0iODAiIHdpZHRoPSIxMjAiIGhlaWdodD0iNDAiIGZpbGw9IiNmOGQ3ZGEiIHN0cm9rZT0iYmxhY2siIHN0cm9rZS13aWR0aD0iMiIgcng9IjUiLz4KICA8dGV4dCB4PSI0NzAiIHk9IjEwNSIgZm9udC1mYW1pbHk9IkFyaWFsIiBmb250LXNpemU9IjE0IiBmaWxsPSJibGFjayIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC13ZWlnaHQ9ImJvbGQiPlRvb2wgLyBFbnY8L3RleHQ+CiAgCiAgPGxpbmUgeDE9IjQ3MCIgeTE9IjEyMCIgeDI9IjQ3MCIgeTI9IjE0MCIgc3Ryb2tlPSJibGFjayIgc3Ryb2tlLXdpZHRoPSIyIiBtYXJrZXItZW5kPSJ1cmwoI2Fycm93KSIvPgogIAogIDxyZWN0IHg9IjQxMCIgeT0iMTQwIiB3aWR0aD0iMTIwIiBoZWlnaHQ9IjMwIiBmaWxsPSIjZjVjNmNiIiBzdHJva2U9ImJsYWNrIiBzdHJva2Utd2lkdGg9IjIiIHJ4PSI1Ii8+CiAgPHRleHQgeD0iNDcwIiB5PSIxNjAiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxMiIgZmlsbD0iYmxhY2siIHRleHQtYW5jaG9yPSJtaWRkbGUiPlJld2FyZCBDYWxjPC90ZXh0PgogIAogIDxsaW5lIHgxPSI0MTAiIHkxPSIxNTUiIHgyPSIyOTAiIHkyPSIxNTUiIHN0cm9rZT0iYmxhY2siIHN0cm9rZS13aWR0aD0iMiIgbWFya2VyLWVuZD0idXJsKCNhcnJvdykiLz4KICAKICA8cmVjdCB4PSIxNzAiIHk9IjE0MCIgd2lkdGg9IjEyMCIgaGVpZ2h0PSIzMCIgZmlsbD0iI2UyZTNmMSIgc3Ryb2tlPSJibGFjayIgc3Ryb2tlLXdpZHRoPSIyIiByeD0iNSIvPgogIDx0ZXh0IHg9IjIzMCIgeT0iMTYwIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTIiIGZpbGw9ImJsYWNrIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj5Qb2xpY3kgVXBkYXRlPC90ZXh0PgogIAogIDxsaW5lIHgxPSIxNzAiIHkxPSIxNTUiIHgyPSIxMTAiIHkyPSIxNTUiIHN0cm9rZT0iYmxhY2siIHN0cm9rZS13aWR0aD0iMiIgbWFya2VyLWVuZD0idXJsKCNhcnJvdykiLz4KICA8bGluZSB4MT0iMTEwIiB5MT0iMTU1IiB4Mj0iMTEwIiB5Mj0iMTIwIiBzdHJva2U9ImJsYWNrIiBzdHJva2Utd2lkdGg9IjIiIG1hcmtlci1lbmQ9InVybCgjYXJyb3cpIi8+CiAgCiAgPHRleHQgeD0iMzAwIiB5PSIzNSIgZm9udC1mYW1pbHk9IkFyaWFsIiBmb250LXNpemU9IjE2IiBmaWxsPSJuYXZ5IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXdlaWdodD0iYm9sZCI+QWdlbnRpYyBSTCDopZTnlKjlj6PpobnlvIDlj7g8L3RleHQ+CiAgCiAgPGRlZnM+CiAgICA8bWFya2VyIGlkPSJhcnJvdyIgdmlld0JveD0iMCAwIDEwIDEwIiByZWZYPSI4IiByZWZZPSI1IiBtYXJrZXJXaWR0aD0iNiIgbWFya2VySGVpZ2h0PSI2IiBvcmllbnQ9ImF1dG8tc3RhcnQtcmV2ZXJzZSI+CiAgICAgIDxwYXRoIGQ9Ik0gMCAwIEwgMTAgNSBMIDAgMTAgeiIgZmlsbD0iYmxhY2siIC8+CiAgICA8L21hcmtlcj4KICA8L2RlZnM+Cjwvc3ZnPg==)
### 💰 步骤 2：计算奖励 (Reward)

Agent 走完轨迹后，需要环境给个“分数”。

**核心代码位置**：`verl/experimental/reward_loop/reward_manager/naive.py`

在 `NaiveRewardManager` 中，奖励计算是**异步**的。
VeRL 不会让 GPU 傻等工具执行完，而是由独立的 `Reward Worker` 去跑。

```python
# 获取 Agent 生成的最终回复
response_str = await self.loop.run_in_executor(None, lambda: self.tokenizer.decode(valid_response_ids...))

# 调用自定义的 compute_score 函数
# 这个函数可以是：
# 1. 规则匹配：response_str == ground_truth ? 1 : 0
# 2. 代码沙盒：跑测试用例，Passed ? 1 : 0
# 3. 模型打分：用另一个 LLM 评判
result = await self.compute_score(
    data_source=data_source,
    solution_str=response_str,
    ground_truth=ground_truth,
    extra_info=extra_info # 包含工具调用历史等
)

return {"reward_score": result, ...}
```

**为什么异步？**
Agent 轨迹可能很长，工具执行（如运行代码、请求 API）可能需要几秒甚至几十秒。如果同步等，GPU 算力就浪费了。VeRL 通过 Ray 异步派发任务，算完再通知 Trainer。

### 📐 步骤 3：计算优势 (Advantage)

拿到 Reward 后，怎么算 Advantage？这是 GRPO/PPO 的核心。

**核心代码位置**：`verl/trainer/ppo/core_algos.py`

VeRL 实现了多种优势估算器，通过 `@register_adv_est` 注册。

#### 1. GRPO (Group Relative Policy Optimization)
目前最流行的算法，省去了 Critic 网络。

```python
@register_adv_est("grpo")
def compute_grpo_outcome_advantage(token_level_rewards, response_mask, index, ...):
    # 1. 对同一个问题的 N 个不同回复，计算总分
    scores = token_level_rewards.sum(dim=-1)
    
    # 2. 按 index (同一组问题) 分组
    id2score = defaultdict(list)
    for i in range(bsz):
        id2score[index[i]].append(scores[i])
        
    # 3. 组内归一化 (Z-score)
    # Advantage = (Score_i - Mean_Group) / (Std_Group + epsilon)
    # 这样 Advantage 就有了正有负，表示“比同组平均水平好还是差”
    for idx in id2score:
        scores_tensor = torch.stack(id2score[idx])
        mean = scores_tensor.mean()
        std = scores_tensor.std()
        scores[idx] = (scores[idx] - mean) / (std + epsilon)
        
    # 4. 广播回 Token 级别，并乘上 response_mask
    return scores.unsqueeze(-1) * response_mask, ...
```

**代码解读**：
- `index` 数组标识了哪些回复属于同一个 Prompt。比如同一个 Prompt 采样了 8 次，它们的 index 就相同。
- `masked_whiten`：进一步做 White-Normalization，让 Advantage 的均值为 0，方差为 1，保证训练稳定。

#### 2. GAE (Generalized Advantage Estimation)
这是传统 PPO 用的，基于 Value Network (Critic) 算出的 TD Error。VeRL 也保留了它，但在 Agent 场景下用得少了。


![GRPO 优势计算流](data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAwIiBoZWlnaHQ9IjE4MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8cmVjdCB4PSIxMCIgeT0iMTAiIHdpZHRoPSI1ODAiIGhlaWdodD0iMTYwIiBmaWxsPSIjZmFmYWZhIiBzdHJva2U9ImJsYWNrIiBzdHJva2Utd2lkdGg9IjIiIHJ4PSIxMCIvPgogIDxyZWN0IHg9IjUwIiB5PSI3MCIgd2lkdGg9IjEwMCIgaGVpZ2h0PSI0MCIgZmlsbD0iI2UwZjdmYSIgc3Ryb2tlPSJibGFjayIgc3Ryb2tlLXdpZHRoPSIyIiByeD0iNSIvPgogIDx0ZXh0IHg9IjEwMCIgeT0iOTUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iYmxhY2siIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtd2VpZ2h0PSJib2xkIj5Qcm9tcHQgeCBOPC90ZXh0PgogIAogIDxsaW5lIHgxPSIxNTAiIHkxPSI5MCIgeDI9IjIwMCIgeTI9IjkwIiBzdHJva2U9ImJsYWNrIiBzdHJva2Utd2lkdGg9IjIiIG1hcmtlci1lbmQ9InVybCgjYXJyb3cyKSIvPgogIDxyZWN0IHg9IjIxMCIgeT0iNzAiIHdpZHRoPSIxMDAiIGhlaWdodD0iNDAiIGZpbGw9IiNmZmY5YzQiIHN0cm9rZT0iYmxhY2siIHN0cm9rZS13aWR0aD0iMiIgcng9IjUiLz4KICA8dGV4dCB4PSIyNjAiIHk9Ijk1IiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTQiIGZpbGw9ImJsYWNrIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXdlaWdodD0iYm9sZCI+TiBSZXNwb25zZXM8L3RleHQ+CiAgCiAgPGxpbmUgeDE9IjMxMCIgeTE9IjkwIiB4Mj0iMzYwIiB5Mj0iOTAiIHN0cm9rZT0iYmxhY2siIHN0cm9rZS13aWR0aD0iMiIgbWFya2VyLWVuZD0idXJsKCNhcnJvdzIpIi8+CiAgPHJlY3QgeD0iMzcwIiB5PSI3MCIgd2lkdGg9IjEwMCIgaGVpZ2h0PSI0MCIgZmlsbD0iI2ZjY2RkMiIgc3Ryb2tlPSJibGFjayIgc3Ryb2tlLXdpZHRoPSIyIiByeD0iNSIvPgogIDx0ZXh0IHg9IjQyMCIgeT0iOTUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iYmxhY2siIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtd2VpZ2h0PSJib2xkIj5SZXdhcmQ8L3RleHQ+CiAgCiAgPGxpbmUgeDE9IjQyMCIgeTE9IjExMCIgeDI9IjQyMCIgeTI9IjEyNSIgc3Ryb2tlPSJibGFjayIgc3Ryb2tlLXdpZHRoPSIyIiBtYXJrZXItZW5kPSJ1cmwoI2Fycm93MikiLz4KICA8cmVjdCB4PSIzNzAiIHk9IjEyNSIgd2lkdGg9IjEwMCIgaGVpZ2h0PSIzMCIgZmlsbD0iI2UxYmVlNyIgc3Ryb2tlPSJibGFjayIgc3Ryb2tlLXdpZHRoPSIyIiByeD0iNSIvPgogIDx0ZXh0IHg9IjQyMCIgeT0iMTQ1IiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTIiIGZpbGw9ImJsYWNrIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj5Ob3JtYWxpemU8L3RleHQ+CiAgCiAgPGxpbmUgeDE9IjM3MCIgeTE9IjE0MCIgeDI9IjI2MCIgeTI9IjE0MCIgc3Ryb2tlPSJibGFjayIgc3Ryb2tlLXdpZHRoPSIyIiBtYXJrZXItZW5kPSJ1cmwoI2Fycm93MikiLz4KICA8cmVjdCB4PSIxNjAiIHk9IjEyNSIgd2lkdGg9IjEwMCIgaGVpZ2h0PSIzMCIgZmlsbD0iI2M4ZTZjOSIgc3Ryb2tlPSJibGFjayIgc3Ryb2tlLXdpZHRoPSIyIiByeD0iNSIvPgogIDx0ZXh0IHg9IjIxMCIgeT0iMTQ1IiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTIiIGZpbGw9ImJsYWNrIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj5BZHZhbnRhZ2U8L3RleHQ+CiAgCiAgPGxpbmUgeDE9IjE2MCIgeTE9IjE0MCIgeDI9IjEwMCIgeTI9IjE0MCIgc3Ryb2tlPSJibGFjayIgc3Ryb2tlLXdpZHRoPSIyIi8+CiAgPGxpbmUgeDE9IjEwMCIgeTE9IjE0MCIgeDI9IjEwMCIgeTI9IjExMCIgc3Ryb2tlPSJibGFjayIgc3Ryb2tlLXdpZHRoPSIyIi8+CiAgPGxpbmUgeDE9IjEwMCIgeTE9IjExMCIgeDI9IjIxMCIgeTI9IjExMCIgc3Ryb2tlPSJibGFjayIgc3Ryb2tlLXdpZHRoPSIyIiBtYXJrZXItZW5kPSJ1cmwoI2Fycm93MikiLz4KICA8dGV4dCB4PSIxNTUiIHk9IjExMCIgZm9udC1mYW1pbHk9IkFyaWFsIiBmb250LXNpemU9IjEwIiBmaWxsPSJncmF5IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj50byBMb3NzPC90ZXh0PgogIAogIDx0ZXh0IHg9IjMwMCIgeT0iMzUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNiIgZmlsbD0iZGFya2dyZWVuIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXdlaWdodD0iYm9sZCI+R1JQTyDotoTlrprplb/pgIHplY3vvIznlKjlu7o8L3RleHQ+CiAgCiAgPGRlZnM+CiAgICA8bWFya2VyIGlkPSJhcnJvdzIiIHZpZXdCb3g9IjAgMCAxMCAxMCIgcmVmWD0iOCIgcmVmWT0iNSIgbWFya2VyV2lkdGg9IjYiIG1hcmtlckhlaWdodD0iNiIgb3JpZW50PSJhdXRvLXN0YXJ0LXJldmVyc2UiPgogICAgICA8cGF0aCBkPSJNIDAgMCBMIDEwIDUgTCAwIDEwIHoiIGZpbGw9ImJsYWNrIiAvPgogICAgPC9tYXJrZXI+CiAgPC9kZWZzPgo8L3N2Zz4=)
### 📉 步骤 4：计算 Loss 与更新

最后，利用 Advantage 和 KL 惩罚来更新模型。

**核心代码位置**：`verl/trainer/ppo/core_algos.py` -> `compute_policy_loss_vanilla`

```python
def compute_policy_loss_vanilla(old_log_prob, log_prob, advantages, response_mask, ...):
    # 1. 计算概率比率 ratio = exp(log_prob - old_log_prob)
    ratio = torch.exp(log_prob - old_log_prob)
    
    # 2. 计算 KL 散度 (衡量新旧策略差异)
    # KL 越大，说明模型偏离旧策略越远
    approx_kl = (old_log_prob - log_prob).mean()
    
    # 3. PPO Clip Loss (核心！)
    # 防止模型因为某一步高 Advantage 就步子迈太大，导致崩溃
    # clip_ratio 通常是 0.2
    surr1 = -advantages * ratio
    surr2 = -advantages * torch.clamp(ratio, 1.0 - 0.2, 1.0 + 0.2)
    
    # 取两者最大值，保证 Loss 下界
    policy_loss = torch.max(surr1, surr2)
    
    # 4. 应用 response_mask
    # 只有 LLM 自己生成的 Token 算 Loss，工具返回的 Token (mask=0) 不算！
    # 这就是 Tool Masking 的作用
    final_loss = (policy_loss * response_mask).sum() / response_mask.sum()
    
    return final_loss, {"kl": approx_kl}
```

### 🧪 总结：一次完整的 Agentic RL 迭代

| 阶段 | 耗时 | 核心操作 | 对应 VeRL 模块 |
| :--- | :--- | :--- | :--- |
| **Rollout** | 长 | LLM 生成 + 工具执行 (AgentLoop) | `agent_loop/` |
| **Reward** | 中 | 异步计算分数 (RewardManager) | `reward_loop/` |
| **Advantage** | 短 | 组内归一化 / GAE 计算 | `core_algos.py` |
| **Update** | 中 | PPO/GRPO Loss 计算 + 梯度反向传播 | `trainer/ppo/` |

通过这套流程，VeRL 实现了**生成、奖励、训练**的高度并行化，这也是它能在千卡集群上高效训练 Agentic RL 的关键。