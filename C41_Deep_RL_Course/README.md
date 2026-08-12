# 深度强化学习与决策

从 C13 表格 RL 跨过「函数逼近」这道坎，进入深度 RL 与决策/控制：DQN、PPO/SAC、离线 RL、基于模型与世界模型、探索与多智能体/序列建模——纯 numpy 自写 toy 环境，从零实现网络与训练循环。

| 模块 | 主题 | 目录 |
|---|---|---|
| 00 | 课程总览与环境 | `00_setup/` |
| 01 | 值函数逼近与 DQN | `01_dqn/` |
| 02 | 策略优化：PPO 与 SAC | `02_ppo_sac/` |
| 03 | 离线强化学习 | `03_offline_rl/` |
| 04 | 基于模型与世界模型 | `04_model_based_world/` |
| 05 | 探索与前沿 | `05_exploration_marl/` |

## 怎么学
每个模块 = `NN_讲解.html`（00 为 `00_overview.html`）先建立算法直觉与数学推导，再跑 `NN_*.ipynb` 用纯 numpy 在自写 toy 环境（GridWorld、numpy 版 CartPole、连续控制玩具）里从零实现网络与训练循环：先看 worked 示例 → ✏️ 练习（TODO + `assert` 判分）→ 📖 参考答案 → 🧪 胶囊兜底自测。网络（小 MLP）、反向传播、优化器、replay buffer、环境全部手写，收敛与回报提升用固定 seed + 稳健阈值保证可复现。所有 notebook 在 CPU 上实跑验证、0 失败。

## 环境
见 `requirements.txt`。核心实现纯 numpy / CPU，自写 toy 环境，无需联网 / GPU / API key，也不依赖 gym 等 RL 框架。固定随机种子保证 assert 可复现。

配套：[术语词典](glossary.md) · [参考清单](references.md)
