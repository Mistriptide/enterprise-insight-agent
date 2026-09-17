# Retrieval Evaluation 实验结果

## 核心指标

| Retriever | Recall@1 | Recall@3 | MRR |
|---|---:|---:|---:|
| keyword | 66.7% | 83.3% | 0.750 |
| vector | 83.3% | 100.0% | 0.917 |

## 逐题排名对比

| ID | Keyword 排名 | Vector 排名 | 对比 | 归因 |
|---|---:|---:|---|---|
| revenue | 1 | 1 | 持平 | 无差异 |
| premium_mix | 1 | 2 | Vector 退化 | Embedding + Chunking |
| sales_route | 1 | 1 | 持平 | 无差异 |
| inventory_efficiency | 1 | 1 | 持平 | 无差异 |
| management_concerns | MISS | 1 | Vector 改善 | Embedding |
| next_priority | 2 | 1 | Vector 改善 | Keyword 检索逻辑 |

## 逐题归因

- **revenue — 无差异：** 两种方法都把包含 2025 与经营收入事实的第 1 页排在首位。
- **premium_mix — Embedding + Chunking：** Vector 将正确页从第 1 名降到第 2 名。问题中的 product tier / sales 与原文 premium products / revenue 存在语义关系，但每个页面被合并为一个宽泛 Chunk，模型把第 2 页的经营管理语境判得更相似。主因是当前 Embedding 在该改写上的区分不足，粗粒度 Chunking 放大了偏差。
- **sales_route — 无差异：** expanded、China 等词面信号已经足够，Embedding 没有带来额外排名收益。
- **inventory_efficiency — 无差异：** management 与库存周转语境使两种方法都能命中第 2 页；当前样本无法证明语义检索更优。
- **management_concerns — Embedding：** Keyword 因 concerns / executives 与 risks / management 没有直接重合而完全漏检；Vector 捕捉到管理层与风险的语义对应关系，从 MISS 提升到第 1 名。
- **next_priority — Keyword 检索逻辑：** Keyword 被 what、the、year 等通用词和第 1 页的 year 频次干扰，只把正确页排在第 2 名；Vector 捕捉 focus / next year 与 2026 priority 的语义关系，将正确页提升到第 1 名。

## 解释边界

- 固定测试集只有 6 道问题和 2 个候选 Chunk。
- Recall@3 在这里接近全语料检查，区分度有限。
- 示例 PDF 为英文且远短于真实中文年报。
- 结果证明了评测流程和当前方法差异，不代表生产级模型质量。
