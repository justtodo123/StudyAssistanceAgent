---
title: Agent 工具编排与状态传递
course: interview
tags: [Agent, Tool Orchestration, 状态]
difficulty: 进阶
updated: 2026-08-18
---

## 面试问题

Agent 工具编排与状态传递：工具编排要定义工具契约、调用顺序、输入输出和失败分支。Agent 不应凭空决定一切，关键步骤需要受控路由和可观察状态。

## 回答要点

多轮流程可以把 QA、Quiz 和 Review-log 串成闭环：先检索讲解，再出题评估，最后记录复习；答错时补充讲解并重试。

## 项目结合点

study-assistant Skill 展示了 6 步闭环，工具调用链可在面试中解释为可验证的状态机，而不是单次黑盒生成。

## 继续追问

如何避免 Agent 无限循环或重复调用工具？
