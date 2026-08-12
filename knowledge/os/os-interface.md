---
title: 操作系统接口
course: os
tags: [接口, Shell, 系统调用, 命令解释器]
difficulty: 入门
updated: 2026-08-12
source: docs/reference/os.md
---

## 一句话概括

OS 向上提供两类接口：**命令接口**（用户直接操作 OS）和**程序接口/系统调用**（程序请求 OS 服务）。Shell 是最常用的命令接口——既是交互界面也是脚本编程环境。

## 核心概念

### 两类接口

| 接口 | 用户 | 形式 | 示例 |
| --- | --- | --- | --- |
| 命令接口 (CLI/GUI) | 人 | 命令行、图形界面 | `ls -l`, 点击删除 |
| 程序接口 (API/系统调用) | 程序 | 函数调用 | `open()`, `fork()` |

### Shell（命令解释器）

- 用户与 OS 内核之间的接口层，**本身不是内核的一部分**
- 工作流程：读取命令 → 解析（变量展开、通配符、重定向）→ 执行 → 显示结果
- 执行方式：
  - **内置命令**（cd/exit）：Shell 自己执行，不创建子进程
  - **外部命令**（grep/find）：fork + exec 创建子进程执行可执行文件

### Shell 核心功能（编程常用）

```bash
# 重定向
ls > output.txt       # stdout→文件
grep error < log.txt  # stdin←文件
make 2>&1 | tee build.log  # stderr→stdout→同时到文件和屏幕

# 管道（Pipe）：进程间数据流转
cat data.csv | grep "os" | sort | uniq -c

# 变量与通配符
echo "User: $USER, Path: $PATH"
ls *.md      # 通配符由 Shell 展开，不是 ls 的参数
```

### 系统调用实现

**syscall 执行路径**：
```
用户程序 → C 库包装函数 → mov eax, __NR_read; int 0x80 (或 sysenter) → 
内核态 → 查系统调用表(sys_call_table[eax]) → sys_read() → 结果返回 → 
iret/sysexit → 用户态 → 库函数返回
```

> 现代 Linux 用 `sysenter`/`syscall` 指令替代旧的 `int 0x80`，更快（少了压栈和检查）。

| 系统调用类别 | 代表性调用 |
| --- | --- |
| 进程控制 | `fork()`, `execve()`, `exit()`, `waitpid()`, `kill()` |
| 文件操作 | `open()`, `read()`, `write()`, `lseek()`, `close()`, `stat()` |
| 目录/文件系统 | `mkdir()`, `rmdir()`, `link()`, `unlink()`, `mount()`, `chdir()` |
| 内存管理 | `brk()`, `mmap()`, `mprotect()` |
| 网络 | `socket()`, `bind()`, `listen()`, `accept()`, `connect()` |
| 信息/杂项 | `getpid()`, `time()`, `sysinfo()`, `uname()` |

### Linux 系统调用的注册与分发

- 系统调用号在 `<sys/syscall.h>` 中定义，`sys_call_table` 存各调用处理函数指针
- 参数传递：x86 用 ebx/ecx/edx/esi/edi 寄存器，x86-64 用 rdi/rsi/rdx/r10/r8/r9
- 最大 6 个参数，更少参数的调用直接忽略不用的寄存器

## 易错点 / 高频考点

- [ ] Shell 是一个**用户态程序**，不是内核的一部分（这经常被问）
- [ ] `cd` 必须是 Shell 内置命令——fork 出来的子进程改 CWD 不影响父进程的当前目录
- [ ] 通配符（`*`）由 Shell 展开，不是被调用程序自己展开的
- [ ] `$PATH` 是 Shell 变量，不是环境变量的全部（`env` 查看真正的环境变量）

## 经典例题

**题干**：解释为什么 `cd` 必须是内置命令而不能是外部可执行文件。
**解答**：外部命令通过 fork+exec 在**子进程**中执行。子进程 chdir 仅改变子进程的工作目录，不影响父进程（即用户当前 Shell）。所以 `cd` 必须由 Shell 自己执行才能改变 Shell 进程的 CWD。

## 关联条目

- [[os-overview]] 操作系统概述（系统调用与双重模式）
- [[process-management]] 进程管理（fork 与 PCB）
- [[linux-case-study]] Linux 实例
- 外部资料索引：[docs/reference/os.md](../../docs/reference/os.md)
