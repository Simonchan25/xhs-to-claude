---
name: share-link
description: Download a shared video/article link from 小红书 (xhs) or Bilibili into `downloads/` so Claude can read it. Use when the user pastes a link from xhslink.com, xiaohongshu.com, b23.tv, or bilibili.com, or asks to "看这个视频/文章/笔记". Produces title, author, desc, cover, full video file + 12 evenly sampled frames (so Claude can "watch" the video), or images for photo notes.
---

# share-link — 手机分享链接 → Claude 可读的本地内容

## 什么时候用

用户在对话里粘贴以下任一域名的链接：
- `xhslink.com/...` — 小红书 App 分享短链
- `xiaohongshu.com/...` — 小红书页面
- `b23.tv/...` — B 站短链
- `bilibili.com/video/...` — B 站视频

或者用户说 "帮我看看这个"、"这个视频/笔记讲了什么"、"这是什么"、"解释一下这个链接" 且消息里有上述链接。

## 怎么用

```bash
python3 ~/.claude/skills/share-link/fetch.py "<url>"
# 输出路径：$PWD/downloads/<时间戳>_<平台>_<id>
# 或覆盖：SHARE_LINK_DOWNLOADS=/some/path python3 ~/.claude/skills/share-link/fetch.py "<url>"
```

下载目录默认跟随**当前工作目录**——在哪个项目启动的 Claude，文件就落在该项目下的 `downloads/`。

然后用 Read 工具读目录里的文件：

- `meta.json` — 结构化元信息（title / author / desc / duration / 视频或图片列表）
- `content.md` — 人读的摘要（标题、作者、文案）
- `cover.jpg` — 封面
- `video.mp4` — 完整视频（xhs 视频笔记）
- `video.txt` / `video.srt` — whisper 转录（纯文本 + 带时间戳字幕）
- `frames/frame_00.jpg` ~ `frame_11.jpg` — 12 帧均匀抽样（用这个"看"视频内容）
- `images/00.jpg ...` — 图文笔记的图片（xhs normal/multi 类型）

## 看视频的做法

视频笔记的核心信息分布在：
1. `content.md` — **先读这个**，已合并 title / author / desc / 全量转录
2. `meta.desc` / `title` — 作者自己写的文案，常常就是核心论点
3. `video.txt` — whisper 转录的纯台词（每一句话）
4. `video.srt` — 带时间戳的字幕，想引用具体时间点用这个
5. `frames/` — 12 帧均匀抽样。Read 若干张看画面（图表、代码、屏幕录制内容）

## 当前支持范围

- ✅ xhs 视频笔记：标题 / 文案 / 作者 / 封面 / 视频 / 12 帧 / **whisper 转录**
- ✅ xhs 图文笔记：标题 / 文案 / 作者 / 封面 / 多图
- ✅ bilibili 视频：标题 / UP主 / 简介 / 封面 / 视频（偏好 H.264）/ 每分钟一帧（12-36）/ **whisper 转录**
- ❌ 评论抓取：未内置

## 转录配置

- 模型默认 `mlx-community/whisper-large-v3-turbo`（中文优秀、M 芯片上 200s 视频≈10s 转完）
- 可覆盖：`SHARE_LINK_WHISPER_MODEL=mlx-community/whisper-medium-mlx python3 fetch.py <url>`
- 跳过转录：`SHARE_LINK_NO_TRANSCRIBE=1 python3 fetch.py <url>`
- 尾部幻觉（连续重复句子）在写入 `video.txt` 前已折叠到最多 2 次

## 依赖

- `python3` + `ffmpeg` / `ffprobe` 必需
- `yt-dlp` 仅 bilibili 需要（`pip install yt-dlp`）；不装时 xhs 链接照常工作
- `mlx_whisper`（转录）可选，不装就自动跳过转录，其他照常。装：`pip install mlx-whisper`（需要 Apple Silicon）
- 注意脚本用 `shutil.which(...)` 在 PATH 里找 yt-dlp / mlx_whisper。切 Python 环境（venv/pyenv）时可能看不到全局装的包，在当前环境补装一次即可
- B 站偏好 H.264（avc1）格式，因为老版 ffmpeg 无法解码 AV1（抽帧会失败）。`-f "bv*[vcodec^=avc1]+ba/..."` 已处理

## 边界情况

- xhs 反爬：脚本用 iOS UA + Referer，目前无需 cookie。若将来失败，在 `http()` 里加 cookie 头
- 外置盘 (`/Volumes/thunderbolt/`) 会生成 `._*` macOS 资源叉文件 —— `frames` 字段已过滤，但目录里视觉上还在，忽略即可
- 视频 URL 有时效签名（`sign=... t=...`），`meta.json` 里的 URL 只在抓取后短时间内有效；下载后的本地文件是稳定的
