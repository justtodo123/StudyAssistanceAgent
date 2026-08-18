# 演示手册 · 离线学习闭环

> 5 分钟内在无 LLM、无 BGE 下载的环境下走通工作台和评测冒烟。
> 对应能力：M5a 评测入口、M5b/M5c 学习会话、M5d 工作台、M5e 一键启动。

## 一键启动

```bash
python tools/start_local.py
```

脚本会以离线 BM25 启动 FastAPI，轮询 `GET /health`，成功后打印工作台地址：

- 工作台：`http://127.0.0.1:8000/`
- 健康检查：`http://127.0.0.1:8000/health`

只检查已启动的服务：

```bash
python tools/start_local.py --check
```

## 演示路径

1. 打开工作台，查看「今日待复习」。
2. 课程选 `操作系统`，主题输入 `死锁`，开始学习。
3. 阅读讲解和来源，回答当前题目。
4. 查看反馈、掌握度评分和下次复习日期。
5. 展开「工具调用轨迹」，对照下面的真实调用链。

## 真实工具调用链

学习会话由服务端编排，前端不复制状态机。一次答对闭环通常是：

```text
create
  -> qa          QaService            检索知识片段
  -> explain     StudySessionService  生成讲解
  -> quiz        QuizService          出 1 道题
  -> evaluate    StudySessionService  确定性评估
  -> review-log  ReviewSchedulerService 记录复习
  -> completed
```

答错一次会进入 `remediation -> retry -> awaiting_answer`；连续两次答错后给出完整参考并结束。

## 评测冒烟

```bash
python tools/run_evaluation.py --smoke
```

CI 使用同一条命令。完整 90 题离线评测仍用：

```bash
python tools/run_evaluation.py
```

## 可选向量模式

默认演示不下载 Hugging Face 模型。若本机已缓存 BGE，可显式打开向量路：

```bash
python tools/start_local.py --use-vector
```

预下载、缓存目录和离线开关见 [platform/README.md](../platform/README.md)。

---

*创建：2026-08-18 · 维护：随演示入口变化同步更新*