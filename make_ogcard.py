# 공유 카드(og_card.png)와 index.html의 메타 설명을 지금 건수로 다시 만든다.
# 빌드 끝에 자동으로 부른다 — 숫자를 손으로 고치면 자동 갱신 때마다 어긋난다.
import re, sys

def build(total, schools, ymin, ymax):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("  (Pillow가 없어 카드 그림은 건너뛴다)"); return False
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), "#f7fafd"); d = ImageDraw.Draw(img)
    for x in range(W):                      # 사이트의 --brand-grad와 같은 띠
        t = x / (W - 1)
        d.line([(x, 0), (x, 14)], fill=(int(0x2d + (0x77 - 0x2d) * t),
                                        int(0xa0 + (0xec - 0xa0) * t),
                                        int(0xdf + (0x77 - 0xdf) * t)))
    F = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
    f = lambda sz, i=0: ImageFont.truetype(F, sz, index=i)
    wm = Image.open("logo_wordmark.png").convert("RGBA")
    wm = wm.resize((int(wm.width * 1.55), int(wm.height * 1.55)), Image.LANCZOS)
    img.paste(wm, (88, 84), wm)
    d.text((88, 236), "공교육 에듀테크 활용 현황", font=f(78, 8), fill="#1d2733")
    d.text((88, 356), "전국 초·중·고가 실제로 사들인 조달 기록으로", font=f(37, 2), fill="#384250")
    d.text((88, 406), "에듀테크 도입 현황을 봅니다", font=f(37, 2), fill="#384250")
    d.line([(88, 494), (1112, 494)], fill="#d6e0eb", width=2)
    d.text((88, 520), f"계약 {total:,}건 · {ymin}~{ymax} · 학교 {schools:,}곳",
           font=f(34, 6), fill="#046ab8")
    d.text((855, 522), "school-edtech.kr", font=f(29, 2), fill="#9298a2")
    img.save("og_card.png", optimize=True)
    return True

def rewrite_meta(total):
    s = open("index.html", encoding="utf-8").read()
    n = f"{total:,}건"
    s2 = re.sub(r"조달 기록 [\d,]+건", f"조달 기록 {n}", s)
    if s2 != s:
        open("index.html", "w", encoding="utf-8").write(s2)
    return s2 != s

if __name__ == "__main__":
    a = sys.argv[1:]
    total, schools = int(a[0]), int(a[1])
    ymin, ymax = (a[2], a[3]) if len(a) > 3 else ("2020", "2026")
    build(total, schools, ymin, ymax)
    rewrite_meta(total)
    print(f"공유 카드·메타 설명 갱신: {total:,}건 · 학교 {schools:,}곳")
