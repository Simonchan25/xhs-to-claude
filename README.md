# xhs（小红书）to claude

> 一个 [Claude Code Skill](https://docs.claude.com/en/docs/claude-code/skills)：把小红书或 B 站的分享链接粘给 Claude，它就能"看"到笔记/视频里的画面、配图和台词。

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Apple Silicon](https://img.shields.io/badge/whisper-Apple%20Silicon-lightgrey.svg)](#依赖)

## 🤔 为什么做

手机刷到好玩的小红书笔记，想丢给 Claude 分析/总结/翻译 —— 但 Claude 打不开反爬的 xhs 页面，看不到视频画面，也听不到音频。这个 skill 解决这个缝隙。

## ✨ 效果

粘一行：

> 上帝视角的量化分析！ http://xhslink.com/o/9A6UY1YlD6g

Claude 自动下载 + 抽帧 + 转录，产生：

```
downloads/<ts>_xhs_<noteId>/
├── content.md      ← 标题 + 作者 + 文案 + 完整转录
├── meta.json
├── cover.jpg
├── video.mp4       ← 视频笔记才有
├── video.txt       ← whisper 转录
├── video.srt
├── frames/         ← 12 张均匀抽帧
└── images/         ← 图文笔记才有
```

然后给你一个**看过画面 + 听过台词**的完整分析。完整输出示例见 [examples/](./examples/)。

## 🚀 安装

```bash
git clone https://github.com/Simonchan25/xhs-to-claude.git
cd xhs-to-claude
bash install.sh

brew install ffmpeg        # 必需
pip install yt-dlp         # B 站需要
pip install mlx-whisper    # 可选，转录用，Apple Silicon
```

`install.sh` 把 `SKILL.md` + `fetch.py` 装到 `~/.claude/skills/share-link/`，所有项目的 Claude Code 会话自动发现。

## 💬 用法

在 Claude Code 任意对话里粘链接：

```
http://xhslink.com/o/xxxxx  帮我分析下这个
```

SKILL 的 description 会匹配 xhs 链接 + "帮我看/分析" 等触发词，Claude 自动调用。

命令行也行：

```bash
python3 ~/.claude/skills/share-link/fetch.py "http://xhslink.com/o/xxxxx"
```

下载落到 `$PWD/downloads/`，不同项目天然隔离。

## ⚙️ 配置

| 环境变量 | 作用 |
|---|---|
| `SHARE_LINK_DOWNLOADS` | 覆盖下载根目录（默认 `$PWD/downloads`） |
| `SHARE_LINK_WHISPER_MODEL` | 转录模型（默认 `mlx-community/whisper-large-v3-turbo`） |
| `SHARE_LINK_NO_TRANSCRIBE=1` | 跳过转录 |

## ✅ 支持

- ✅ 小红书图文笔记：标题 / 文案 / 作者 / 封面 / 多图
- ✅ 小红书视频笔记：以上全部 + 视频 + 12 帧 + whisper 转录
- ✅ B 站视频：标题 / UP主 / 简介 / 封面 / 视频（偏好 H.264）+ 每分钟一帧（12-36 之间）+ whisper 转录

## 📦 依赖

- Python ≥ 3.9、`ffmpeg`（必需）
- `yt-dlp`（B 站需要；`pip install yt-dlp`）
- `mlx-whisper`（可选，仅 Apple Silicon；没装自动跳过转录）
- [Claude Code](https://docs.claude.com/en/docs/claude-code/overview)

## 📄 License

[MIT](./LICENSE)
