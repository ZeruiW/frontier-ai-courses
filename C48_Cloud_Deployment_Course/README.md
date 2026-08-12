# LLM 生产部署与云原生

模型跑得快不等于服务活得下来：容器化、服务契约、Kubernetes 编排、渐进发布与自动扩缩、云平台与成本——
用纯 Python 把控制平面的逻辑从零实现一遍，并为每个机制算一笔 SLO 账、容量账与成本账。

| 模块 | 主题 | 目录 |
|---|---|---|
| 00 | 课程总览与环境 | `00_setup/` |
| 01 | 容器化：可复现的运行时 | `01_containerization/` |
| 02 | 推理服务 API | `02_serving_api/` |
| 03 | Kubernetes 编排 | `03_kubernetes/` |
| 04 | 发布策略与自动扩缩 | `04_rollout_autoscaling/` |
| 05 | 云平台、集群调度与成本 | `05_cloud_scheduling_cost/` |

## 这门课补什么洞
C24（高效推理服务）讲引擎**内部**怎么跑得快；C37（MLOps）讲模型**生命周期**怎么管。
中间那段——**这个引擎怎么被打包、被调度、被发布、被扩缩、被计费**——本课补上。
它也是「LLM Research Engineer」类岗位 JD 里 `Docker / Kubernetes / cloud / MLOps 协作` 那几条的正面回应。

## 怎么学
每个模块 = `NN_讲解.html`（00 为 `00_overview.html`）先建立生产系统的设计直觉与三笔账，
再跑 `NN_*.ipynb` 用纯标准库/numpy 从零实现控制平面：
镜像层缓存与冷启动分解 → SSE 编解码与 Erlang-C 容量模型 → reconcile 循环/探针状态机/装箱调度器 →
滚动更新仿真/SPRT 序贯检验/HPA 闭环震荡 → spot 期望成本/backfill 调度器/$per-1M-token 分解。
先看 worked 示例（print + assert 自检）→ ✏️ 练习（TODO + `assert` 判分）→ 📖 参考答案 → 🧪 真实量级胶囊。
所有 notebook 在 CPU 上实跑验证、0 失败。

## 环境
见 `requirements.txt`。核心实现纯标准库 + numpy，**不需要 Docker / Kubernetes / GPU / 云账号 / 联网**。
讲解里的 Dockerfile、Kubernetes YAML、Slurm `sbatch` 脚本是可直接使用的正确写法，仅作对照展示、不参与运行。
所有价格与性能数字均为公开量级的约数，notebook 顶部可改成你自己的报价。

配套：[术语词典](glossary.md) · [参考清单](references.md)
