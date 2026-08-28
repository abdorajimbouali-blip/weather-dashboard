#!/usr/bin/env python3
"""Assemble a Darija promo video from stills + narration."""
import os
import subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import arabic_reshaper
from bidi.algorithm import get_display

ROOT = os.path.dirname(os.path.abspath(__file__))
FFMPEG = "/tmp/videnv/lib/python3.11/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
W, H = 1920, 1080
FPS = 25
OUT = os.path.join(os.path.dirname(ROOT), "qanat_tasmeem_mawaqi.mp4")

SCENES = [
    {
        "img": "scene1_intro.jpg",
        "audio": "n1.mp3",
        "title": "قناة تصميم المواقع",
        "sub": "احترافية · عصرية · بالمغربية",
    },
    {
        "img": "scene2_problem.jpg",
        "audio": "n2.mp3",
        "title": "موقعك كيعكس خدمتك",
        "sub": "ما تخليش التصميم يضعّف المشروع",
    },
    {
        "img": "scene3_responsive.jpg",
        "audio": "n3.mp3",
        "title": "تصميم عصري ومتجاوب",
        "sub": "تليفون · تابليت · كمبيوتر",
    },
    {
        "img": "scene4_process.jpg",
        "audio": "n4.mp3",
        "title": "من الفكرة حتى الإطلاق",
        "sub": "هوية بصرية · تجربة مستخدم · برمجة",
    },
    {
        "img": "scene5_channel.jpg",
        "audio": "n5.mp3",
        "title": "نصائح وأعمال حقيقية",
        "sub": "شروحات · أفكار · مشاريع",
    },
    {
        "img": "scene6_cta.jpg",
        "audio": "n6.mp3",
        "title": "تابعونا دابا",
        "sub": "فعلو الجرس وبداو المشروع",
    },
]


def ar_text(s: str) -> str:
    return get_display(arabic_reshaper.reshape(s))


def probe_duration(path: str) -> float:
    r = subprocess.run(
        [FFMPEG, "-i", path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    for line in r.stderr.splitlines():
        if "Duration:" in line:
            t = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = t.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    raise RuntimeError(f"no duration for {path}")


def draw_lower_third(im: Image.Image, title: str, sub: str) -> Image.Image:
    im = im.convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    # top cinematic bar
    for y in range(140):
        a = int(160 * (1 - y / 140))
        d.line([(0, y), (W, y)], fill=(8, 12, 22, a))

    # bottom gradient
    for y in range(H - 320, H):
        t = (y - (H - 320)) / 320
        a = int(230 * t)
        d.line([(0, y), (W, y)], fill=(6, 10, 20, a))

    # gold accent line
    d.rectangle([80, H - 168, 80 + 220, H - 162], fill=(212, 175, 90, 255))

    title_font = ImageFont.truetype(FONT, 64)
    sub_font = ImageFont.truetype(FONT_REG, 32)

    t = ar_text(title)
    s = ar_text(sub)
    d.text((80, H - 148), t, font=title_font, fill=(255, 252, 245, 255))
    d.text((80, H - 72), s, font=sub_font, fill=(212, 175, 90, 255))

    # small brand chip top-right
    chip = ar_text("تصميم مواقع احترافي")
    chip_font = ImageFont.truetype(FONT_REG, 26)
    bbox = d.textbbox((0, 0), chip, font=chip_font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad_x, pad_y = 22, 12
    x1, y1 = W - 80 - tw - pad_x * 2, 36
    x2, y2 = W - 80, 36 + th + pad_y * 2
    d.rounded_rectangle([x1, y1, x2, y2], radius=10, fill=(8, 12, 22, 170))
    d.rectangle([x1, y1, x1 + 6, y2], fill=(212, 175, 90, 255))
    d.text((x1 + pad_x + 6, y1 + pad_y - 2), chip, font=chip_font, fill=(255, 252, 245, 255))

    out = im.convert("RGBA")
    out = Image.alpha_composite(out, overlay)
    # slight contrast
    rgb = out.convert("RGB")
    rgb = ImageEnhance.Contrast(rgb).enhance(1.06)
    rgb = ImageEnhance.Color(rgb).enhance(1.08)
    return rgb


def main():
    clips = []
    for i, sc in enumerate(SCENES, 1):
        src = os.path.join(ROOT, sc["img"])
        framed = os.path.join(ROOT, f"framed_{i:02d}.jpg")
        clip = os.path.join(ROOT, f"clip_{i:02d}.mp4")
        audio = os.path.join(ROOT, sc["audio"])

        img = Image.open(src)
        framed_img = draw_lower_third(img, sc["title"], sc["sub"])
        framed_img.save(framed, quality=93, optimize=True)

        dur = probe_duration(audio) + 0.25  # tiny tail
        frames = max(int(round(dur * FPS)), 25)
        # Slow Ken Burns zoom
        vf = (
            f"scale=8000:-1,"
            f"zoompan=z='min(zoom+0.00045,1.10)':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s={W}x{H}:fps={FPS},"
            f"fade=t=in:st=0:d=0.35,fade=t=out:st={max(dur-0.35,0)}:d=0.35"
        )
        cmd = [
            FFMPEG, "-y",
            "-loop", "1", "-i", framed,
            "-i", audio,
            "-vf", vf,
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-t", f"{dur:.3f}",
            "-movflags", "+faststart",
            clip,
        ]
        print("building", clip, "dur", dur)
        subprocess.check_call(cmd)
        clips.append(clip)

    lst = os.path.join(ROOT, "concat.txt")
    with open(lst, "w") as f:
        for c in clips:
            f.write(f"file '{c}'\n")

    tmp = os.path.join(ROOT, "concat.mp4")
    subprocess.check_call([
        FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", lst,
        "-c", "copy", tmp,
    ])

    # final pass: slight audio loudnorm
    subprocess.check_call([
        FFMPEG, "-y", "-i", tmp,
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        OUT,
    ])
    print("WROTE", OUT, os.path.getsize(OUT))


if __name__ == "__main__":
    main()
