# 공유 카드(og_card.png)와 index.html의 메타 설명을 지금 건수로 다시 만든다.
# 빌드 끝에 자동으로 부른다 — 숫자를 손으로 고치면 자동 갱신 때마다 어긋난다.
import re, sys

def build(total, schools, ymin, ymax):
    """카드에는 로고와 제목만 둔다 — 건수·설명·주소까지 적었더니 카카오톡 미리보기에서 글이 너무 많았다(2026-09-16 사용자).
    건수는 og:description(rewrite_meta)에만 남긴다. 로고는 원본(logo_stack_src.png)을 읽어 줄여 선명하게 만든다."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("  (Pillow가 없어 카드 그림은 건너뛴다)"); return False
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), "#ffffff"); d = ImageDraw.Draw(img)   # 로고 원본 바탕이 흰색이라 카드도 흰색
    for x in range(W):                      # 사이트의 --brand-grad와 같은 띠
        t = x / (W - 1)
        d.line([(x, 0), (x, 14)], fill=(int(0x2d + (0x77 - 0x2d) * t),
                                        int(0xa0 + (0xec - 0xa0) * t),
                                        int(0xdf + (0x77 - 0xdf) * t)))
    F = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
    f = lambda sz, i=0: ImageFont.truetype(F, sz, index=i)
    src = "logo_stack_src.png" if __import__("os").path.exists("logo_stack_src.png") else "logo_stack.png"
    wm = Image.open(src).convert("RGBA")          # 원본은 읽기만 한다 — 저장하지 않는다
    bbox = wm.getbbox()
    if bbox:
        wm = wm.crop(bbox)
    lh = 250
    wm = wm.resize((int(wm.width * lh / wm.height), lh), Image.LANCZOS)
    title, tf = "공교육 에듀테크 활용 현황", f(74, 8)
    tw = d.textlength(title, font=tf)
    gap = 44
    block_h = lh + gap + 88
    y0 = (H - 14 - block_h) // 2 + 14
    img.paste(wm, ((W - wm.width) // 2, y0), wm)
    d.text(((W - tw) / 2, y0 + lh + gap), title, font=tf, fill="#1d2733")
    img.save("og_card.png", optimize=True)
    return True

def rewrite_meta(total, schools, ymin, ymax):
    s = open("index.html", encoding="utf-8").read()
    # 미리보기·검색 설명·이미지 대체문에는 건수를 적지 않는다 — 건수는 매달 바뀌어 공유된 글마다 달라진다(2026-09-16 사용자).
    # 화면 안의 숫자는 여전히 meta로 들어간다. 아래 치환은 옛 판에 남은 건수 표기가 있을 때만 고친다.
    s2 = re.sub(r"조달 기록 [\d,]+건으로 보는 공교육 에듀테크 도입 현황\.", "공공 조달 기록으로 확인하는 서비스입니다.", s)
    # 카카오톡 미리보기의 설명은 건수 없이 한 줄 — 건수는 계속 바뀌어 공유된 글마다 달라진다(2026-09-16 사용자)
    s2 = re.sub(r'(<meta property="og:description" content=")[^"]*(")',
                lambda m: f'{m.group(1)}전국 초·중·고가 어떤 에듀테크를 쓰는지 공공 조달 기록으로 확인합니다{m.group(2)}', s2)
    # og:image:alt도 건수·학교 수를 적는다 — 여기만 빠뜨려 307,093건·10,502곳이 계속 남아 있었다
    # (2026-09-12 확인). 화면에 보이는 숫자는 빌드가 만든다는 규칙은 메타태그에도 똑같이 적용된다.
    s2 = re.sub(r'(<meta property="og:image:alt" content=")[^"]*(")',
                lambda x: f"{x.group(1)}school edtech 로고와 제목 ‘공교육 에듀테크 활용 현황’{x.group(2)}", s2)
    if s2 != s:
        open("index.html", "w", encoding="utf-8").write(s2)
    return s2 != s

if __name__ == "__main__":
    a = sys.argv[1:]
    total, schools = int(a[0]), int(a[1])
    ymin, ymax = (a[2], a[3]) if len(a) > 3 else ("2020", "2026")
    build(total, schools, ymin, ymax)
    rewrite_meta(total, schools, ymin, ymax)
    print(f"공유 카드·메타 설명 갱신: {total:,}건 · 학교 {schools:,}곳")
