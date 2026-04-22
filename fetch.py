#!/usr/bin/env python3
"""Fetch xhs / bilibili share links into downloads/<ts>_<platform>/.

Usage: python fetch.py <url>
Output: prints the absolute output dir path on success.
"""
import sys, os, re, json, shutil, subprocess, urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path

WHISPER_MODEL = os.environ.get("SHARE_LINK_WHISPER_MODEL", "mlx-community/whisper-large-v3-turbo")
TRANSCRIBE = os.environ.get("SHARE_LINK_NO_TRANSCRIBE") != "1"

UA_IOS = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
DOWNLOADS = Path(os.environ.get("SHARE_LINK_DOWNLOADS") or (Path.cwd() / "downloads")).resolve()


def http(url, binary=False, referer=None):
    req = urllib.request.Request(url)
    req.add_header("User-Agent", UA_IOS)
    if referer:
        req.add_header("Referer", referer)
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
        return (data if binary else data.decode("utf-8", "ignore"), r.geturl())


def unesc(s):
    # field value extracted from embedded JSON: decode \u00xx escapes
    try:
        return json.loads('"' + s + '"')
    except Exception:
        return s


def slugify(s, n=40):
    s = re.sub(r"[\s/\\:*?\"<>|]+", "_", s).strip("_")
    return s[:n] or "note"


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe_duration(path):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)])
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def extract_frames(video, outdir, duration, n=12):
    outdir.mkdir(exist_ok=True)
    if duration <= 0:
        run(["ffmpeg", "-i", str(video), "-vf", "fps=1/10", "-q:v", "4",
             str(outdir / "frame_%03d.jpg"), "-y", "-loglevel", "error"])
        return
    step = duration / n
    for i in range(n):
        t = min(step * (i + 0.5), max(0.0, duration - 0.2))
        run(["ffmpeg", "-ss", f"{t:.2f}", "-i", str(video),
             "-frames:v", "1", "-q:v", "4",
             str(outdir / f"frame_{i:02d}.jpg"), "-y", "-loglevel", "error"])


def dedupe_consecutive(text, max_repeat=2):
    lines = text.splitlines()
    out, last, count = [], None, 0
    for ln in lines:
        key = ln.strip()
        if key == last and key:
            count += 1
            if count <= max_repeat:
                out.append(ln)
        else:
            last, count = key, 1
            out.append(ln)
    return "\n".join(out)


def transcribe(video_path, outdir):
    if not TRANSCRIBE or not shutil.which("mlx_whisper"):
        return None
    r = run(["mlx_whisper", str(video_path),
             "--model", WHISPER_MODEL,
             "--language", "zh",
             "--output-format", "all",
             "--output-dir", str(outdir),
             "--verbose", "False"])
    if r.returncode != 0:
        return {"error": r.stderr[-500:]}
    stem = video_path.stem
    txt_path = outdir / f"{stem}.txt"
    if txt_path.exists():
        cleaned = dedupe_consecutive(txt_path.read_text())
        txt_path.write_text(cleaned)
    return {
        "txt": f"{stem}.txt" if (outdir / f"{stem}.txt").exists() else None,
        "srt": f"{stem}.srt" if (outdir / f"{stem}.srt").exists() else None,
        "model": WHISPER_MODEL,
    }


def fetch_xhs(url, outdir):
    html, final = http(url)
    title_m = re.search(r'"title":"([^"]*)"', html)
    desc_m = re.search(r'"desc":"([^"]*)"', html)
    type_m = re.search(r'"type":"(video|normal|multi)"', html)
    title = unesc(title_m.group(1)) if title_m else ""
    desc = unesc(desc_m.group(1)) if desc_m else ""
    type_ = type_m.group(1) if type_m else "unknown"

    nicks = re.findall(r'"nickname":"([^"]+)"', html)
    author = Counter(map(unesc, nicks)).most_common(1)[0][0] if nicks else ""

    note_id_m = re.search(r"/(?:discovery/item|explore)/([a-f0-9]+)", final)
    note_id = note_id_m.group(1) if note_id_m else ""

    meta = {"platform": "xhs", "url": final, "noteId": note_id,
            "type": type_, "title": title, "author": author, "desc": desc}

    covers = re.findall(r'"cover":\{[^}]*"url":"([^"]+)"', html)
    if covers:
        try:
            (outdir / "cover.jpg").write_bytes(
                http(unesc(covers[0]), binary=True, referer="https://www.xiaohongshu.com/")[0])
            meta["cover"] = "cover.jpg"
        except Exception as e:
            meta["coverError"] = str(e)

    if type_ == "video":
        master = re.findall(r'"masterUrl":"([^"]+)"', html)
        uniq = []
        seen = set()
        for u in map(unesc, master):
            if u not in seen:
                seen.add(u); uniq.append(u)
        meta["videoUrls"] = uniq
        if uniq:
            vp = outdir / "video.mp4"
            vp.write_bytes(http(uniq[0], binary=True, referer="https://www.xiaohongshu.com/")[0])
            meta["videoFile"] = "video.mp4"
            dur = probe_duration(vp)
            meta["duration"] = round(dur, 2)
            extract_frames(vp, outdir / "frames", dur)
            meta["frames"] = sorted(p.name for p in (outdir / "frames").glob("*.jpg") if not p.name.startswith("._"))
            tr = transcribe(vp, outdir)
            if tr:
                meta["transcript"] = tr
    elif type_ in ("normal", "multi"):
        def _fid(u):
            return u.split("?")[0].rsplit("/", 1)[-1].split("!")[0]
        raw = re.findall(r'"url":"(http[^"]*xhscdn[^"]*)"', html)
        raw += re.findall(r'"urlDefault":"([^"]+)"', html)
        decoded = [unesc(u) for u in raw]
        candidates = [u for u in decoded
                      if "sns-avatar" not in u and "emoji" not in u
                      and "!style_" not in u
                      and _fid(u).startswith("1040g")]
        seen = set(); uniq = []
        for u in candidates:
            fid = _fid(u)
            if fid in seen:
                continue
            seen.add(fid); uniq.append(u)
        # fallback: if prefix filter stripped everything (older format), loosen
        if not uniq:
            for u in decoded:
                if "sns-avatar" in u or "emoji" in u: continue
                fid = _fid(u)
                if fid and fid not in seen:
                    seen.add(fid); uniq.append(u)
        idir = outdir / "images"; idir.mkdir(exist_ok=True)
        saved = []
        for i, u in enumerate(uniq[:20]):
            try:
                (idir / f"{i:02d}.jpg").write_bytes(
                    http(u, binary=True, referer="https://www.xiaohongshu.com/")[0])
                saved.append(f"images/{i:02d}.jpg")
            except Exception:
                pass
        meta["images"] = saved
    return meta


def fetch_bilibili(url, outdir):
    if not shutil.which("yt-dlp"):
        return {"platform": "bilibili", "url": url,
                "error": "yt-dlp not installed — run: pip install yt-dlp"}
    probe = run(["yt-dlp", "--dump-single-json", "--no-download", "--no-playlist", url])
    if probe.returncode != 0:
        return {"platform": "bilibili", "url": url, "error": probe.stderr[-500:]}
    info = json.loads(probe.stdout)
    meta = {
        "platform": "bilibili",
        "url": url,
        "bvid": info.get("id", ""),
        "title": info.get("title", ""),
        "author": info.get("uploader", ""),
        "desc": info.get("description", "") or "",
        "duration": round(info.get("duration") or 0, 2),
    }
    thumb = info.get("thumbnail")
    if thumb:
        try:
            (outdir / "cover.jpg").write_bytes(http(thumb, binary=True)[0])
            meta["cover"] = "cover.jpg"
        except Exception as e:
            meta["coverError"] = str(e)
    # Prefer H.264 (avc) over AV1 — older ffmpeg installs can't decode av1 for frame extraction
    dl = run(["yt-dlp",
              "-f", "bv*[vcodec^=avc1]+ba/bv*[vcodec^=avc]+ba/b[vcodec^=avc]/bv*+ba/b",
              "--merge-output-format", "mp4",
              "--no-playlist",
              "-o", str(outdir / "video.%(ext)s"),
              "--quiet", "--no-progress",
              url])
    if dl.returncode != 0:
        meta["videoError"] = dl.stderr[-500:]
        return meta
    vids = [p for p in outdir.glob("video.*")
            if p.suffix.lower() in (".mp4", ".mkv", ".flv", ".webm")
            and not p.name.startswith("._")]
    if not vids:
        meta["videoError"] = "no video file produced"
        return meta
    vp = vids[0]
    meta["videoFile"] = vp.name
    dur = meta["duration"] or probe_duration(vp)
    meta["duration"] = round(dur, 2)
    # longer videos get more frames (~1/min, capped 36); short videos stay at 12
    n = min(max(12, int(dur / 60)), 36)
    extract_frames(vp, outdir / "frames", dur, n=n)
    meta["frames"] = sorted(p.name for p in (outdir / "frames").glob("*.jpg")
                            if not p.name.startswith("._"))
    tr = transcribe(vp, outdir)
    if tr:
        meta["transcript"] = tr
    return meta


def detect(url):
    if "xiaohongshu.com" in url or "xhslink.com" in url: return "xhs"
    if "bilibili.com" in url or "b23.tv" in url: return "bilibili"
    return "unknown"


def main():
    if len(sys.argv) < 2:
        print("usage: fetch.py <url>", file=sys.stderr); sys.exit(1)
    url = sys.argv[1].strip()
    if "xhslink.com" in url or "b23.tv" in url:
        _, url = http(url)
    plat = detect(url)
    if plat == "unknown":
        print(f"unsupported url: {url}", file=sys.stderr); sys.exit(2)

    DOWNLOADS.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = slugify(url.split("?")[0].rstrip("/").split("/")[-1])
    outdir = DOWNLOADS / f"{ts}_{plat}_{slug}"
    outdir.mkdir(parents=True, exist_ok=True)

    meta = fetch_xhs(url, outdir) if plat == "xhs" else fetch_bilibili(url, outdir)
    (outdir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    body = f"# {meta.get('title','')}\n\n**作者**：{meta.get('author','')}\n**平台**：{meta.get('platform','')}\n**链接**：{meta.get('url','')}\n"
    if meta.get("duration"):
        body += f"**时长**：{meta['duration']}s\n"
    body += f"\n## 文案\n\n{meta.get('desc','')}\n"
    tr = meta.get("transcript") or {}
    if tr.get("txt"):
        transcript_text = (outdir / tr["txt"]).read_text().strip()
        body += f"\n## 音频转录（whisper）\n\n{transcript_text}\n"
    (outdir / "content.md").write_text(body)
    print(str(outdir))


if __name__ == "__main__":
    main()
