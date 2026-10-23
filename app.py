import os, uuid, json, re, shutil, subprocess, asyncio
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import httpx

BASE = Path(__file__).parent.resolve()
STATIC = BASE / "static"
WORK = BASE / "work"
WORK.mkdir(exist_ok=True)
MAX_BYTES = 250 * 1024 * 1024
MAX_SECONDS = 120
ALLOWED_VIDEO = {".mp4", ".mov", ".m4v", ".webm"}
ALLOWED_IMAGE = {".jpg", ".jpeg", ".png", ".webp"}

app = FastAPI(title="AI MAGIC EDITOR")
app.mount("/static", StaticFiles(directory=STATIC), name="static")

def ffmpeg_available():
    return shutil.which("ffmpeg") is not None

def probe(path: Path):
    if not shutil.which("ffprobe"):
        raise HTTPException(503, "FFprobe is missing. Install FFmpeg/FFprobe on the server.")
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=20).decode().strip()
        return float(out)
    except Exception:
        raise HTTPException(400, "Hindi mabasa ang video file. Subukan ang MP4 o MOV.")

async def parse_command(command: str):
    # Optional server-side AI interpretation. A safe local parser remains available.
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.post(
                    "https://api.openai.com/v1/responses",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
                        "input": [
                            {"role":"system","content":"Convert a user's video-editing request into ONLY JSON with keys: start_seconds (number or null), end_seconds (number or null), brightness (-0.5 to 0.5), contrast (0.5 to 2), saturation (0 to 2), speed (0.5 to 2), aspect ('9:16'|'16:9'|'1:1'|null), subtitles (boolean), subtitle_text (string or null), mute (boolean), cinematic (boolean). Do not invent subtitle dialogue. Use null/defaults when uncertain. The output must be valid JSON."},
                            {"role":"user","content":command}
                        ]
                    }
                )
                r.raise_for_status()
                data = r.json()
                text = ""
                for item in data.get("output", []):
                    for c in item.get("content", []):
                        if c.get("type") == "output_text":
                            text += c.get("text", "")
                plan = json.loads(text.strip().removeprefix("```json").removesuffix("```").strip())
                return sanitize_plan(plan)
        except Exception:
            pass

    c = command.lower()
    p = {"start_seconds":None,"end_seconds":None,"brightness":0.0,"contrast":1.0,"saturation":1.0,"speed":1.0,"aspect":None,"subtitles":False,"subtitle_text":None,"mute":False,"cinematic":False}
    if "cinematic" in c or "movie" in c or "pelikula" in c:
        p.update(cinematic=True, contrast=1.15, saturation=0.88)
    if "bright" in c or "liwanag" in c:
        p["brightness"] = 0.12
    if "dark" in c or "madilim" in c:
        p["brightness"] = -0.12
    if "black and white" in c or "black-and-white" in c or "grayscale" in c:
        p["saturation"] = 0
    if "slow motion" in c or "slow-mo" in c or "bagalan" in c:
        p["speed"] = 0.5
    if "fast" in c or "bilisan" in c:
        p["speed"] = 1.5
    if "vertical" in c or "tiktok" in c or "reels" in c or "9:16" in c:
        p["aspect"] = "9:16"
    elif "square" in c or "1:1" in c:
        p["aspect"] = "1:1"
    elif "landscape" in c or "16:9" in c or "youtube" in c:
        p["aspect"] = "16:9"
    if "mute" in c or "walang tunog" in c:
        p["mute"] = True
    if "subtitle" in c or "caption" in c or "subtitles" in c or "caption" in c:
        p["subtitles"] = True
        # User can provide explicit text after "text:"
        m = re.search(r"(?:text|subtitle|caption)\s*:\s*(.+)", command, re.I)
        if m: p["subtitle_text"] = m.group(1).strip()
    # Explicit trim syntax: "trim 5 to 20" or "cut 5-20"
    m = re.search(r"(?:trim|cut|tanggalin)\s+(\d+(?:\.\d+)?)\s*(?:to|hanggang|-)\s*(\d+(?:\.\d+)?)", c)
    if m:
        p["start_seconds"], p["end_seconds"] = float(m.group(1)), float(m.group(2))
    return sanitize_plan(p)

def sanitize_plan(p):
    defaults = {"start_seconds":None,"end_seconds":None,"brightness":0.0,"contrast":1.0,"saturation":1.0,"speed":1.0,"aspect":None,"subtitles":False,"subtitle_text":None,"mute":False,"cinematic":False}
    out = defaults.copy()
    for k in defaults:
        if k in p: out[k] = p[k]
    for k, lo, hi in [("brightness",-0.5,0.5),("contrast",0.5,2),("saturation",0,2),("speed",0.5,2)]:
        try: out[k] = max(lo, min(hi, float(out[k])))
        except: out[k] = defaults[k]
    for k in ("start_seconds","end_seconds"):
        if out[k] is not None:
            try: out[k] = max(0, float(out[k]))
            except: out[k] = None
    if out["aspect"] not in ("9:16","16:9","1:1",None): out["aspect"] = None
    out["subtitles"] = bool(out["subtitles"])
    out["mute"] = bool(out["mute"])
    out["cinematic"] = bool(out["cinematic"])
    if out["subtitle_text"] is not None: out["subtitle_text"] = str(out["subtitle_text"])[:1000]
    return out

def cleanup(paths):
    for p in paths:
        try:
            if p and Path(p).exists(): Path(p).unlink()
        except: pass

@app.get("/", response_class=HTMLResponse)
async def home():
    return (STATIC / "index.html").read_text(encoding="utf-8")

@app.get("/api/health")
async def health():
    return {"ok": True, "ffmpeg": ffmpeg_available(), "max_video_seconds": MAX_SECONDS}

@app.post("/api/edit")
async def edit(background_tasks: BackgroundTasks, file: UploadFile = File(...), command: str = Form(...)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_VIDEO | ALLOWED_IMAGE:
        raise HTTPException(415, "Hindi suportado ang file. Gumamit ng MP4/MOV o JPG/PNG/WebP.")
    content = await file.read()
    if not content or len(content) > MAX_BYTES:
        raise HTTPException(413, "Walang laman ang file o lumampas sa 250 MB.")
    job = uuid.uuid4().hex
    source = WORK / f"{job}{ext}"
    output = WORK / f"{job}_edited.mp4" if ext in ALLOWED_VIDEO else WORK / f"{job}_edited.png"
    source.write_bytes(content)

    if ext in ALLOWED_VIDEO:
        if not ffmpeg_available():
            cleanup([source])
            raise HTTPException(503, "Hindi naka-install ang FFmpeg sa server. I-install muna ito.")
        duration = probe(source)
        if duration > MAX_SECONDS + 0.25:
            cleanup([source])
            raise HTTPException(400, f"Ang video ay {duration:.1f} seconds. Maximum ay 120 seconds; i-trim muna ito.")
        plan = await parse_command(command)
        start = plan["start_seconds"] or 0
        end = plan["end_seconds"] if plan["end_seconds"] is not None else duration
        if start >= end or start >= duration:
            cleanup([source])
            raise HTTPException(400, "Trim range ay hindi valid. Halimbawa: 'trim 5 to 20'.")
        end = min(end, duration)
        filters = []
        filters.append(f"eq=brightness={plan['brightness']}:contrast={plan['contrast']}:saturation={plan['saturation']}")
        if plan["aspect"] == "9:16":
            filters.append("scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280")
        elif plan["aspect"] == "1:1":
            filters.append("scale=720:720:force_original_aspect_ratio=increase,crop=720:720")
        elif plan["aspect"] == "16:9":
            filters.append("scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720")
        vf = ",".join(filters)
        cmd = ["ffmpeg","-y","-ss",str(start),"-i",str(source),"-t",str(end-start)]
        if plan["mute"]:
            cmd += ["-an"]
        elif plan["speed"] != 1:
            cmd += ["-filter:a",f"atempo={plan['speed']}"]
        if plan["speed"] != 1:
            vf += f",setpts={1/plan['speed']}*PTS"
        cmd += ["-vf",vf,"-c:v","libx264","-preset","veryfast","-crf","23"]
        if not plan["mute"] and plan["speed"] == 1:
            cmd += ["-c:a","aac","-b:a","128k"]
        elif not plan["mute"] and plan["speed"] != 1:
            cmd += ["-c:a","aac","-b:a","128k"]
        cmd += ["-movflags","+faststart",str(output)]
        try:
            proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=240)
            if proc.returncode != 0:
                raise RuntimeError(stderr.decode(errors="ignore")[-1200:])
        except asyncio.TimeoutError:
            cleanup([source, output])
            raise HTTPException(504, "Nag-timeout ang pag-edit. Subukan ang mas maliit na file.")
        except Exception as e:
            cleanup([source, output])
            raise HTTPException(500, "Hindi natapos ang video processing. Suriin kung tama ang FFmpeg installation.")
        background_tasks.add_task(cleanup, [str(source), str(output)])
        return FileResponse(output, media_type="video/mp4", filename="ai-magic-edited.mp4", background=background_tasks,
                            headers={"X-Edit-Plan": json.dumps(plan)})
    else:
        # Basic image MVP: pass-through image output; photo-specific AI transformations need an image service.
        try:
            from PIL import Image, ImageEnhance
            img = Image.open(source).convert("RGB")
            c = command.lower()
            if "black and white" in c or "grayscale" in c:
                img = ImageEnhance.Color(img).enhance(0)
            if "bright" in c or "liwanag" in c:
                img = ImageEnhance.Brightness(img).enhance(1.15)
            if "dark" in c or "madilim" in c:
                img = ImageEnhance.Brightness(img).enhance(0.85)
            if "contrast" in c or "cinematic" in c:
                img = ImageEnhance.Contrast(img).enhance(1.15)
            img.save(output, format="PNG")
        except Exception:
            cleanup([source, output])
            raise HTTPException(400, "Hindi ma-edit ang image file.")
        background_tasks.add_task(cleanup, [str(source), str(output)])
        return FileResponse(output, media_type="image/png", filename="ai-magic-edited.png", background=background_tasks)
