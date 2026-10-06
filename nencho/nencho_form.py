#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""令和8年分 年末調整の質問用紙（従業員記入用）PDF生成スクリプト

使い方:
  python3 nencho_form.py --out-dir out            # 空欄版と記入例の両方を生成
  python3 nencho_form.py --out-dir out --blank    # 空欄版のみ
  python3 nencho_form.py --out-dir out --sample   # 記入例のみ

必要: reportlab, BIZ UDPGothic (Regular/Bold) の TTF（--font-dir で指定。既定は ./fonts）
"""
import argparse
import os
import sys

from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

YEAR = "令和8年"        # 対象年分
NEXT_YEAR = "令和9年"   # 翌年
TOTAL_PAGES = 6

W, H = A4
ML, MR, MT, MB = 46.0, 36.0, 34.0, 30.0
CW = W - ML - MR  # content width

RED = HexColor("#c8102e")
RED_LIGHT = HexColor("#f4c7cd")
GRAY = HexColor("#444444")
MID = HexColor("#777777")
LIGHT = HexColor("#e9e9e9")
BAND = HexColor("#dcdcdc")
BLUE = HexColor("#1f4e9c")

F = "UD"
FB = "UDB"

# 字下げ・禁則
NO_HEAD = set("、。，．・）」』】〕〉》〗〙〟’”ゝゞ々ーぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ！？!?:;：；,.)]}")
NO_TAIL = set("（「『【〔〈《〖〘〝‘“([{")


FONT_FILES = ("BIZUDPGothic-Regular.ttf", "BIZUDPGothic-Bold.ttf")
FONT_URL = "https://raw.githubusercontent.com/googlefonts/morisawa-biz-ud-gothic/main/fonts/ttf/"
IPA_FALLBACK = "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf"


def register_fonts(font_dir):
    """BIZ UDPゴシック（SIL OFL）を登録。無ければ Google Fonts の GitHub から取得し、それも無理なら IPA P ゴシックで代用。"""
    os.makedirs(font_dir, exist_ok=True)
    paths = [os.path.join(font_dir, f) for f in FONT_FILES]
    if not all(os.path.exists(p) for p in paths):
        import urllib.request
        for f, p in zip(FONT_FILES, paths):
            if os.path.exists(p):
                continue
            try:
                print(f"フォントを取得します: {FONT_URL}{f}")
                urllib.request.urlretrieve(FONT_URL + f, p)
            except Exception as e:  # noqa: BLE001
                print(f"  取得失敗: {e}")
    if all(os.path.exists(p) for p in paths):
        pdfmetrics.registerFont(TTFont(F, paths[0]))
        pdfmetrics.registerFont(TTFont(FB, paths[1]))
    elif os.path.exists(IPA_FALLBACK):
        print("BIZ UDPゴシックが無いため IPA P ゴシックで代用します（太字は同一フォント）")
        pdfmetrics.registerFont(TTFont(F, IPA_FALLBACK))
        pdfmetrics.registerFont(TTFont(FB, IPA_FALLBACK))
    else:
        sys.exit("フォントが見つかりません。--font-dir に BIZUDPGothic-Regular.ttf / -Bold.ttf を置いてください。")


class Form:
    """A4縦・上から下へ描いていく簡易レイアウタ。sample が None なら空欄版。"""

    def __init__(self, path, sample=None, title=""):
        self.c = canvas.Canvas(path, pagesize=A4)
        self.c.setTitle(title)
        self.c.setAuthor("鮎澤パートナーズ")
        self.sample = sample
        self.page = 0
        self.y = H - MT
        self.warnings = []
        self.limit = W - MR + 0.5

    def _chk(self, xend, what):
        if xend > self.limit + 0.6:
            self.warnings.append(f"p{self.page} y={self.y:.0f} over by {xend - self.limit:.1f}pt: {what[:40]}")

    # ------------------------------------------------------------------ text
    def sw(self, s, size, bold=False):
        return pdfmetrics.stringWidth(s, FB if bold else F, size)

    def text(self, x, y, s, size=9.5, bold=False, color=black):
        self.c.setFillColor(color)
        self.c.setFont(FB if bold else F, size)
        self.c.drawString(x, y, s)
        xe = x + self.sw(s, size, bold)
        self._chk(xe, s)
        return xe

    def text_right(self, xr, y, s, size=9.5, bold=False, color=black):
        self.c.setFillColor(color)
        self.c.setFont(FB if bold else F, size)
        self.c.drawRightString(xr, y, s)

    def wrap(self, s, size, maxw, bold=False):
        lines = []
        for para in s.split("\n"):
            cur = ""
            for ch in para:
                if self.sw(cur + ch, size, bold) <= maxw:
                    cur += ch
                else:
                    if ch in NO_HEAD and cur:
                        if len(cur) > 1 and cur[-1] not in NO_HEAD:
                            lines.append(cur[:-1])   # 追い出し
                            cur = cur[-1] + ch
                        else:
                            cur += ch
                        continue
                    if cur and cur[-1] in NO_TAIL:
                        carry = cur[-1]
                        lines.append(cur[:-1])
                        cur = carry + ch
                    else:
                        lines.append(cur)
                        cur = ch
            lines.append(cur)
        return lines

    def para(self, s, x=None, size=9.0, color=black, maxw=None, leading=None, bold=False, indent=0):
        """段落を描き、y を進める。"""
        x = ML if x is None else x
        maxw = (W - MR - x) if maxw is None else maxw
        leading = leading or size * 1.42
        lines = self.wrap(s, size, maxw - indent, bold)
        for i, ln in enumerate(lines):
            self.y -= leading
            self.text(x + (indent if i else 0), self.y, ln, size, bold, color)
        return self.y

    def note(self, s, x=None, size=8.3, indent=0):
        return self.para(s, x=x, size=size, color=GRAY, indent=indent, leading=size * 1.4)

    def down(self, n):
        self.y -= n

    # -------------------------------------------------------------- controls
    def _tick(self, cx, cy, r=3.6, color=None):
        """記入例用の✓（赤）。中心 (cx, cy)。"""
        c = self.c
        c.saveState()
        c.setStrokeColor(color or RED)
        c.setLineWidth(1.5)
        c.setLineCap(1)
        p = c.beginPath()
        p.moveTo(cx - r * 0.85, cy + r * 0.05)
        p.lineTo(cx - r * 0.2, cy - r * 0.7)
        p.lineTo(cx + r * 1.05, cy + r * 0.95)
        c.drawPath(p, stroke=1, fill=0)
        c.restoreState()

    def _is_on(self, key):
        return bool(self.sample) and key is not None and key in self.sample.get("checks", set())

    def radio(self, x, label, key=None, size=9.5, y=None, bold=False):
        """○（どれか1つ）。戻り値は次のx。"""
        y = self.y if y is None else y
        c = self.c
        r = 5.2
        cx, cy = x + r + 0.5, y + 3.4
        c.setStrokeColor(black)
        c.setLineWidth(0.9)
        c.circle(cx, cy, r, stroke=1, fill=0)
        if self._is_on(key):
            self._tick(cx, cy, color=BLUE if key in self.sample.get("blue", set()) else RED)
        return self.text(x + 2 * r + 4.0, y, label, size, bold) + 11

    def check(self, x, label, key=None, size=9.5, y=None, bold=False):
        """□（当てはまるもの全部）。戻り値は次のx。"""
        y = self.y if y is None else y
        c = self.c
        s = 10.4
        bx, by = x + 0.5, y - 1.8
        c.setStrokeColor(black)
        c.setLineWidth(0.9)
        c.rect(bx, by, s, s, stroke=1, fill=0)
        if self._is_on(key):
            self._tick(bx + s / 2, by + s / 2, color=BLUE if key in self.sample.get("blue", set()) else RED)
        return self.text(x + s + 4.5, y, label, size, bold) + 11

    def field(self, x, label, width, key=None, unit="", size=9.5, y=None, gap=3.0, value_size=None, bold=False):
        """ラベル＋下線の記入欄。戻り値は次のx。"""
        y = self.y if y is None else y
        if label:
            x = self.text(x, y, label, size, bold) + gap
        self.c.setStrokeColor(black)
        self.c.setLineWidth(0.8)
        self.c.line(x, y - 2.2, x + width, y - 2.2)
        self._chk(x + width, "field:" + (label or key or ""))
        if self.sample and key is not None and self.sample.get("fields", {}).get(key):
            v = str(self.sample["fields"][key])
            vs = value_size or size + 0.5
            self.c.setFillColor(BLUE if key in self.sample.get("blue", set()) else RED)
            self.c.setFont(F, vs)
            tw = self.sw(v, vs)
            if tw > width - 2:
                vs = max(6.5, vs * (width - 2) / tw)
                self.c.setFont(F, vs)
            self.c.drawString(x + 3, y, v)
        x = x + width
        if unit:
            x = self.text(x + 2, y, unit, size)
        return x + 12

    def boxes(self, x, n, key=None, y=None, s=13.0, group=4):
        """マイナンバー等の1文字1マス。"""
        y = self.y if y is None else y
        c = self.c
        c.setStrokeColor(black)
        c.setLineWidth(0.7)
        val = ""
        if self.sample and key is not None:
            val = str(self.sample.get("fields", {}).get(key, ""))
        cx = x
        for i in range(n):
            c.rect(cx, y - 3.5, s, s + 1.5, stroke=1, fill=0)
            if i < len(val):
                c.setFillColor(RED)
                c.setFont(F, 10.5)
                c.drawCentredString(cx + s / 2, y, val[i])
            cx += s
            if group and (i + 1) % group == 0 and i + 1 < n:
                cx += 4
        return cx + 8

    def arrow(self, x, y=None, size=9.5):
        y = self.y if y is None else y
        return self.text(x, y, "→", size, color=GRAY) + 5

    def jump(self, x, label, y=None):
        """設問ジャンプ（▶ Aへ）。直前の選択肢に密着させる。"""
        y = self.y if y is None else y
        return self.text(x - 6, y, "▶ " + label, 9.5, bold=True, color=BLUE) + 14

    def badge(self, kind, xr=None, y=None):
        """設問見出し右端のバッジ。kind: 'one'（どれか1つ）/ 'all'（全部）。"""
        y = self.y if y is None else y
        xr = (W - MR) if xr is None else xr
        c = self.c
        if kind == "one":
            label = "どれか1つに✓"
            fill = HexColor("#eaf1fb")
            edge = BLUE
        else:
            label = "当てはまるもの全部に✓"
            fill = HexColor("#fff4de")
            edge = HexColor("#b36b00")
        size = 7.6
        tw = self.sw(label, size)
        icon = 10
        w = tw + icon + 12
        h = 12.5
        x0 = xr - w
        c.setFillColor(fill)
        c.setStrokeColor(edge)
        c.setLineWidth(0.6)
        c.roundRect(x0, y - 3.2, w, h, 3, stroke=1, fill=1)
        # icon
        c.setStrokeColor(edge)
        if kind == "one":
            c.circle(x0 + 7.5, y + 3.0, 3.3, stroke=1, fill=0)
        else:
            c.rect(x0 + 4.3, y - 0.2, 6.5, 6.5, stroke=1, fill=0)
        self.text(x0 + icon + 5, y, label, size, color=edge)
        return x0

    # ------------------------------------------------------------- structure
    def header(self, title):
        self.page += 1
        self.y = H - MT
        c = self.c
        self.text(ML, self.y, f"{YEAR}分　年末調整の質問用紙", 8.0, color=GRAY)
        self.text_right(W - MR, self.y, f"{self.page}／{TOTAL_PAGES}", 8.0, color=GRAY)
        self.y -= 15
        if self.sample:
            x = self.text(ML, self.y, "記入例（架空の方の例です）", 9.0, bold=True, color=RED)
            x = self.text(x + 8, self.y, "赤字＝あなたが書く所", 7.8, color=RED)
            self.text(x + 6, self.y, "青字＝勤め先の方が書く所", 7.8, color=BLUE)
        xr = W - MR
        nx = xr - 190
        self.field(nx, "お名前", 150, key="name", size=9.0, bold=True, gap=6)
        self.y -= 8
        c.setStrokeColor(black)
        c.setLineWidth(1.2)
        c.line(ML, self.y, W - MR, self.y)
        self.y -= 4
        if title:
            self.page_title(title)

    def watermark(self):
        c = self.c
        c.saveState()
        c.setFillColor(HexColor("#888888"))
        try:
            c.setFillAlpha(0.08)
        except Exception:
            pass
        c.setFont(FB, 110)
        c.translate(W / 2, H * 0.30)
        c.rotate(30)
        c.drawCentredString(0, -40, "記入例")
        c.restoreState()

    def footer(self):
        self.text(ML, MB - 6, "鮎澤パートナーズ　年末調整の質問用紙（令和8年分）", 6.5, color=MID)
        if self.sample:
            self.text_right(W - MR, MB - 8, "※ これは記入例です（架空の方の例）。実際の用紙は白紙です。", 8.5, bold=True, color=RED)

    def newpage(self):
        if self.y < MB + 6:
            self.warnings.append(f"p{self.page}: bottom overflow y={self.y:.0f}")
        self.footer()
        self.c.showPage()

    def section(self, title):
        self.y -= 6
        c = self.c
        c.setFillColor(BAND)
        c.setStrokeColor(BAND)
        c.rect(ML, self.y - 6, CW, 17, stroke=0, fill=1)
        self.text(ML + 6, self.y - 1.5, title, 11.0, bold=True)
        self.y -= 10

    def q(self, num, text, kind=None, star=False):
        """設問見出し。kind: 'one'/'all'/None。"""
        self.y -= 17
        x = ML
        x = self.text(x, self.y, num, 10.5, bold=True, color=BLUE) + 6
        if star:
            x = self.text(x, self.y, "★", 10.0, color=RED) + 1
        right = W - MR
        if kind:
            right = self.badge(kind) - 6
        lines = self.wrap(text, 10.0, right - x, bold=True)
        self.text(x, self.y, lines[0], 10.0, bold=True)
        for ln in lines[1:]:
            self.y -= 13.5
            self.text(x, self.y, ln, 10.0, bold=True)
        self.y -= 3

    def frame_begin(self, title=None, x=None, w=None, fill=None, lw=1.0):
        """枠の開始。戻り値は frame_end に渡す。fill を指定すると背景を塗る（勤め先欄など）。"""
        x = ML if x is None else x
        w = CW if w is None else w
        top = self.y - 4
        if title:
            self.y -= 8
        return (x, w, top, title, fill, lw)

    def frame_end(self, f, pad=6):
        x, w, top, title, fill, lw = f
        bottom = self.y - pad
        c = self.c
        if fill is not None:
            # 背景を先に塗る（既に描いた文字の下に敷くため、透過塗り）
            c.saveState()
            c.setFillColor(fill)
            try:
                c.setFillAlpha(0.35)
            except Exception:
                pass
            c.rect(x, bottom, w, top - bottom, stroke=0, fill=1)
            c.restoreState()
        c.setStrokeColor(black)
        c.setLineWidth(lw)
        c.rect(x, bottom, w, top - bottom, stroke=1, fill=0)
        if title:
            tw = self.sw(title, 9.5, True)
            c.setFillColor(white)
            c.rect(x + 6, top - 4.5, tw + 6, 10, stroke=0, fill=1)
            self.text(x + 9, top - 3.2, title, 9.5, bold=True)
        self.y = bottom - 2

    def page_title(self, title):
        self.y -= 15
        self.text(ML, self.y, title, 14.5, bold=True)
        self.y -= 6

    def hr(self, light=True):
        self.c.setStrokeColor(LIGHT if light else black)
        self.c.setLineWidth(0.5)
        self.c.line(ML, self.y - 3, W - MR, self.y - 3)

    def lines(self, n, gap=15):
        for _ in range(n):
            self.y -= gap
            self.c.setStrokeColor(black)
            self.c.setLineWidth(0.5)
            self.c.line(ML + 6, self.y - 2, W - MR - 6, self.y - 2)

    def save(self):
        if self.y < MB + 6:
            self.warnings.append(f"p{self.page}: bottom overflow y={self.y:.0f}")
        self.footer()
        self.c.save()
        for w in self.warnings:
            print("  WARN", w)


# ============================================================ 記入例データ
SAMPLE = {
    "fields": {
        "name": "山田　太郎",
        "due_m": "11", "due_d": "20", "to": "総務の佐藤",
        "q1_name": "山田　太郎",
        "q1_kana_sei": "ヤマダ", "q1_kana_mei": "タロウ",
        "q1_y": "60", "q1_m": "6", "q1_d": "15",
        "q1_zip1": "123", "q1_zip2": "4567",
        "q1_addr1": "〇〇県〇〇市〇〇町1-2-3",
        "q1_addr2": "〇〇マンション〇〇号",
        "q9a_name": "山田　花子", "q9a_kana": "ヤマダ　ハナコ",
        "q9a_y": "62", "q9a_m": "8", "q9a_d": "10",
        "q9a_salary": "150",
        "f1_name": "山田　一郎", "f1_kana": "ヤマダ　イチロウ",
        "f1_y": "19", "f1_m": "5", "f1_d": "5", "f1_salary": "150",
        "f1_addr": "〇〇県〇〇市〇〇町4-5-6（大学の近くで一人暮らし）", "f1_send_v": "60",
        "f2_name": "山田　さくら", "f2_kana": "ヤマダ　サクラ",
        "f2_y": "28", "f2_m": "3", "f2_d": "3",
        "q13_1_co": "〇〇生命", "q13_1_to": "山田　花子", "q13_1_rel": "妻",
        "q13_2_co": "△△生命", "q13_2_to": "山田　太郎", "q13_2_rel": "本人",
        "q14_1_co": "〇〇損害保険",
        "q17_co": "株式会社〇〇", "q17_m": "3", "q17_d": "31",
        "q18_inc_who": "一郎", "q18_inc_v": "120",
        "q19_hoken_n": "3", "q19_gensen_n": "1",
        "sig_m": "11", "sig_d": "10", "sig_name": "山田　太郎",
        "mn_self_name": "山田　太郎", "mn_self": "111111111111",
        "mn_sp_name": "山田　花子",
        "mn_f1_name": "山田　一郎", "mn_f1": "999999999999",
        "mn_f2_name": "山田　さくら",
        "emp_date": "令和8年11月20日", "emp_by": "佐藤",
    },
    "blue": {"due_m", "due_d", "to", "how_paper", "scope_all", "emp_card", "emp_date", "emp_by", "emp_use_shaho"},
    "checks": {
        "how_paper", "scope_all",
        "q1_male", "q1_showa",
        "q2_no", "q3_same", "q3_juminhyo_same", "q4_self", "q5_no",
        "q6_no", "q7_no", "q8_no",
        "q9_yes", "q9a_wife", "q9a_showa", "q9a_live_tog", "q9a_dis_no", "q9a_inc_yes", "q9a_inc_salary", "q9a_senju_no",
        "fam_yes",
        "f1_rel_child", "f1_heisei", "f1_dis_no", "f1_live_sep", "f1_send_yes", "f1_inc_yes", "f1_inc_salary",
        "f2_rel_child", "f2_heisei", "f2_dis_no", "f2_live_tog", "f2_inc_no",
        "q10_no", "q11_no",
        "q12_yes", "q12_life", "q12_quake", "q12_all_ok",
        "q13_1_life", "q13_2_nenkin",
        "q14_1_self",
        "q16_no",
        "q17_yes", "q17_kou", "q17_gensen_yes",
        "q18_yes", "q18_inc",
        "q19_yes", "q19_hoken", "q19_gensen",
        "mn_sp_before", "mn_f2_before",
        "emp_card",
    },
}

ORANGE = HexColor("#b36b00")


# ============================================================== 共通部品
def birth(d, x, p, with_reiwa=False, size=9.5):
    """生年月日：○昭和 ○平成 (○令和) ○西暦 __年 __月 __日"""
    x = d.radio(x, "昭和", key=f"{p}_showa", size=size)
    x = d.radio(x, "平成", key=f"{p}_heisei", size=size)
    if with_reiwa:
        x = d.radio(x, "令和", key=f"{p}_reiwa", size=size)
    x = d.radio(x, "西暦", key=f"{p}_seireki", size=size)
    x = d.field(x - 4, "", 30, key=f"{p}_y", unit="年", size=size)
    x = d.field(x - 4, "", 22, key=f"{p}_m", unit="月", size=size)
    x = d.field(x - 4, "", 22, key=f"{p}_d", unit="日", size=size)
    return x


def income_lines_person(d, p, x0):
    """配偶者用の収入明細（複数✓）。"""
    x = x0
    x = d.check(x, "給料・パート", key=f"{p}_inc_salary")
    x = d.field(x, "", 40, key=f"{p}_salary", unit="万円")
    x = d.check(x, "年金（遺族年金・障害年金は除く）", key=f"{p}_inc_pension")
    x = d.field(x, "", 40, key=f"{p}_pension", unit="万円")
    d.y -= 15
    x = x0
    x = d.check(x, "商売・業務委託", key=f"{p}_inc_biz")
    x = d.field(x, "売上", 40, key=f"{p}_biz_s", unit="万円")
    x = d.field(x, "経費", 40, key=f"{p}_biz_e", unit="万円")
    x = d.text(x, d.y, "青色申告", 9.0) + 4
    x = d.radio(x, "している", key=f"{p}_blue_yes", size=9.0)
    x = d.radio(x, "していない", key=f"{p}_blue_no", size=9.0)
    x = d.radio(x, "不明", key=f"{p}_blue_unknown", size=9.0)
    d.y -= 15
    x = x0
    x = d.check(x, "退職金", key=f"{p}_inc_retire")
    x = d.field(x, "", 40, key=f"{p}_retire", unit="万円")
    x = d.check(x, "そのほか（満期金・株など。種類", key=f"{p}_inc_other")
    x = d.field(x, "", 70, key=f"{p}_other_t")
    x = d.text(x - 6, d.y, "）", 9.5) + 3
    d.field(x, "", 40, key=f"{p}_other_v", unit="万円")


def gate_line(d, x, no_label, no_key, yes_label, yes_key, tail, tail_color=None, jump=None):
    """○ない ○ある → 説明 の定型行。"""
    x = d.radio(x, no_label, key=no_key)
    if jump:
        x = d.jump(x, jump)
    x = d.radio(x, yes_label, key=yes_key)
    x = d.arrow(x)
    if tail:
        x = d.text(x, d.y, tail, 9.0, color=tail_color or black)
    return x


# ============================================================== pages
def page1(d: Form):
    d.header(None)
    d.y -= 20
    d.text(ML, d.y, f"{YEAR}分　年末調整の質問用紙", 17, bold=True)
    d.y -= 6
    d.para("12月のお給料で、今年1年分の所得税を精算します（年末調整）。そのために、あなたとご家族のこと、"
           "払った保険料などを教えてください。この答えをもとに、勤め先が頼んでいる会計事務所（税理士事務所）が、あなたの申告書を作ります。"
           "書いた内容は年末調整にだけ使い、勤め先と税理士事務所（守秘義務があります）だけが見ます。",
           size=9.5)
    d.y -= 6

    f = d.frame_begin("勤め先の方が書いてから配ってください", fill=LIGHT)
    d.y -= 15
    x = ML + 8
    x = d.text(x, d.y, "出す日", 9.5, bold=True) + 6
    x = d.field(x, "", 26, key="due_m", unit="月")
    x = d.field(x, "", 26, key="due_d", unit="日まで")
    x += 6
    x = d.text(x, d.y, "出す先", 9.5, bold=True) + 6
    x = d.field(x, "", 90, key="to", unit="さん")
    x += 6
    x = d.text(x, d.y, "出し方", 9.5, bold=True) + 6
    x = d.radio(x, "紙で渡す", key="how_paper")
    d.radio(x, "写真に撮って送る", key="how_photo")
    d.y -= 15
    x = ML + 8
    x = d.text(x, d.y, "書いてもらう範囲", 9.5, bold=True) + 6
    x = d.radio(x, "全部", key="scope_all")
    d.radio(x, "一部だけ（今年この勤め先で年末調整をしない方）", key="scope_min")
    d.note("「一部だけ」＝Q1〜Q4・5ページの署名・6ページの「あなた」の行。写真で送る場合は、会計事務所が案内する専用フォルダへ。"
           "6ページ（マイナンバー）だけは紙で渡すか、専用フォルダへ（LINE・メールは不可）。印刷は1〜5ページを両面、6ページは別の紙に片面で。"
           "ご家族が4人以上の方には、3ページと6ページを2枚ずつ渡してください。", x=ML + 8)
    d.frame_end(f)

    f = d.frame_begin("書き方")
    d.y -= 15
    x = ML + 10
    x = d.text(x, d.y, "1", 9.5, bold=True) + 6
    x = d.text(x, d.y, "印の違い：", 9.5, bold=True) + 4
    saved = d.sample
    d.sample = {"checks": {"lg1", "lg2", "lg3"}, "fields": {}}
    x = d.radio(x, "は", key=None)
    x = d.text(x - 10, d.y, "どれか1つ", 9.5, bold=True, color=BLUE) + 2
    x = d.text(x, d.y, "だけに✓　　", 9.5)
    x = d.check(x, "は", key=None)
    x = d.text(x - 10, d.y, "当てはまるもの全部", 9.5, bold=True, color=ORANGE) + 2
    x = d.text(x, d.y, "に✓（いくつでも）", 9.5)
    d.y -= 14
    x = ML + 24
    x = d.text(x, d.y, "例）", 8.5, color=GRAY) + 2
    x = d.radio(x, "いいえ", key=None, size=8.5)
    x = d.radio(x, "はい", key="lg1", size=8.5)
    x = d.text(x + 8, d.y, "例）", 8.5, color=GRAY) + 2
    x = d.check(x, "生命保険", key="lg2", size=8.5)
    x = d.check(x, "地震保険", key="lg3", size=8.5)
    x = d.check(x, "国民年金", key=None, size=8.5)
    d.text(x + 4, d.y, "✓は、レ点でも塗りつぶしでも結構です。", 8.5, color=GRAY)
    d.sample = saved
    d.y -= 2
    for n, s_ in [
        ("2", "★印の所は必ず書いてください。ほかは、分からないところは空けたままで結構です（会計事務所からお尋ねします）。"),
        ("3", "金額は、だいたいで結構です（1万円単位）。生まれた日は西暦でも結構です。間違えたら二重線で消して書き直してください（印鑑は要りません）。"),
        ("4", "保険の控除証明書（はがき）などは、この用紙にクリップで留めて出してください。写真で出す方は、はがきの表と裏を1枚ずつ、文字が読めるように撮ってください。"),
        ("5", "マイナンバーは、最後の6ページだけに書いてください。書き終わった用紙は、ほかの人に見せたりコピーを残したりしないでください。"),
    ]:
        d.y -= 1
        yy = d.y
        d.para(s_, x=ML + 22, size=9.0, leading=12.5)
        d.text(ML + 10, yy - 12.5, n, 9.5, bold=True)
    d.frame_end(f)

    d.page_title("あなたのこと")
    d.q("Q1", "お名前・フリガナ・生年月日・住所", star=True)
    d.y -= 14
    x = ML + 8
    x = d.field(x, "お名前（住民票のとおり）", 170, key="q1_name", value_size=11)
    d.field(x, "通称名がある方", 120, key="q1_alias")
    d.y -= 17
    x = ML + 8
    x = d.field(x, "フリガナ", 95, key="q1_kana_sei")
    x = d.field(x, "", 95, key="q1_kana_mei")
    x += 6
    x = d.text(x, d.y, "性別", 9.5) + 6
    x = d.radio(x, "男", key="q1_male")
    x = d.radio(x, "女", key="q1_female")
    d.y -= 17
    x = ML + 8
    x = d.text(x, d.y, "生年月日", 9.5) + 8
    birth(d, x, "q1")
    d.y -= 17
    x = ML + 8
    x = d.text(x, d.y, "住所", 9.5) + 8
    x = d.text(x, d.y, "〒", 9.5) + 3
    x = d.field(x, "", 34, key="q1_zip1")
    x = d.text(x - 10, d.y, "-", 9.5) + 2
    x = d.field(x, "", 44, key="q1_zip2")
    d.text(x, d.y, "（各ページの右上にも、お名前を書いてください）", 8.0, color=GRAY)
    d.y -= 17
    d.field(ML + 8, "", CW - 16, key="q1_addr1")
    d.y -= 17
    d.field(ML + 8, "", CW - 16, key="q1_addr2")
    d.note("（2行目：マンション名・部屋番号など）", x=ML + 8)

    d.q("Q2", "今年、名字（姓）が変わりましたか。", kind="one")
    d.y -= 14
    x = ML + 8
    x = d.radio(x, "いいえ", key="q2_no")
    x = d.radio(x, "はい", key="q2_yes")
    x = d.arrow(x)
    x = d.field(x, "前の名字", 80, key="q2_old")
    x = d.field(x, "変わった月", 22, key="q2_m", unit="月")
    x = d.text(x, d.y, "理由", 9.5) + 4
    x = d.radio(x, "結婚", key="q2_marry")
    x = d.radio(x, "離婚", key="q2_div")
    d.radio(x, "そのほか", key="q2_other")
    d.note("（前の名字で届いたはがきや源泉徴収票も、そのまま出して結構です）", x=ML + 8)

    d.q("Q3", f"来年（{NEXT_YEAR}）1月1日に住んでいる所は、上の住所と同じですか。", kind="one", star=True)
    d.y -= 14
    x = ML + 8
    x = d.radio(x, "同じ", key="q3_same")
    x = d.radio(x, "引っ越した・引っ越す予定", key="q3_move")
    x = d.arrow(x)
    d.field(x, "新しい住所", W - MR - x - 60, key="q3_addr")
    d.y -= 15
    x = ML + 8
    x = d.text(x, d.y, "住民票の住所は、上の住所と", 9.5) + 6
    x = d.radio(x, "同じ", key="q3_juminhyo_same")
    x = d.radio(x, "違う", key="q3_juminhyo_diff")
    x = d.arrow(x)
    d.field(x, "住民票の住所", W - MR - x - 70, key="q3_juminhyo_addr")
    d.note("（住民税は、1月1日に住んでいる市区町村に納めるため、お聞きしています）", x=ML + 8)

    d.q("Q4", "住民票の「世帯主」はどなたですか。", kind="one")
    d.y -= 14
    x = ML + 8
    x = d.radio(x, "あなた", key="q4_self")
    x = d.radio(x, "ほかの方", key="q4_other")
    x = d.arrow(x)
    x = d.field(x, "お名前", 110, key="q4_name")
    d.field(x, "あなたから見て（父・母・夫・妻など）", 60, key="q4_rel")
    d.note("（世帯主＝住民票のいちばん上に名前がある方。一人暮らしなら「あなた」、実家なら父・母など。分からなければ空欄で結構です）", x=ML + 8)

    d.q("Q5", "この勤め先のほかにも、いま給料をもらっている勤め先はありますか。", kind="one")
    d.y -= 14
    x = ML + 8
    x = d.radio(x, "ない", key="q5_no")
    x = d.radio(x, "ある", key="q5_yes")
    x = d.arrow(x)
    x = d.text(x, d.y, "あなたの「メイン」の勤め先は", 9.5) + 6
    x = d.radio(x, "この勤め先", key="q5_main_here")
    x = d.radio(x, "ほかの勤め先", key="q5_main_other")
    d.radio(x, "わからない", key="q5_unknown")
    d.y -= 15
    x = ML + 24
    d.field(x, "ほかの勤め先の名前", 160, key="q5_name")
    d.note("メイン＝給料が多い方、または「扶養控除等申告書」（家族のことを書く紙）を出した方。「ほかの勤め先」がメインの方は、年末調整はそちらでするのが原則です"
           "（会計事務所からご案内します）。どの方も、この用紙はこのまま続けて書いてください。ほかの勤め先の給料は、2ページのQ6にも書いてください。", x=ML + 8)
    d.newpage()


def page2(d: Form):
    d.header("あなたの収入と状況・配偶者")
    d.q("Q6", "この勤め先の給料のほかに、今年（1月〜12月）に入るお金はありますか。", kind="one")
    d.y -= 14
    x = ML + 8
    gate_line(d, x, "ない", "q6_no", "ある", "q6_yes", "当てはまるもの全部に✓を付けて、額面（税金や保険料が引かれる前の額）をだいたいで")
    d.y -= 15
    x = ML + 20
    x = d.check(x, "ほかの勤め先の給料", key="q6_salary")
    x = d.field(x, "", 40, key="q6_salary_v", unit="万円")
    d.text(x, d.y, "（年末調整には入りません。確定申告が要ることがあります）", 7.8, color=GRAY)
    d.y -= 14.5
    x = ML + 20
    x = d.check(x, "年金（老齢・厚生・企業年金・iDeCoの年金受取）", key="q6_pension")
    x = d.field(x, "", 40, key="q6_pension_v", unit="万円")
    d.text(x, d.y, "※遺族年金・障害年金は書かないでください", 7.8, color=GRAY)
    d.y -= 14.5
    x = ML + 20
    x = d.check(x, "保険会社の個人年金・満期金・解約金", key="q6_insurance")
    x = d.field(x, "受け取った額", 40, key="q6_insurance_v", unit="万円")
    d.text(x, d.y, "→ 保険会社の「お知らせ」も一緒に", 7.8, color=GRAY)
    d.y -= 14.5
    x = ML + 20
    x = d.check(x, "退職金・iDeCoの一時金", key="q6_retire")
    x = d.field(x, "額面", 40, key="q6_retire_v", unit="万円")
    x = d.field(x, "勤めた年数", 26, key="q6_retire_y", unit="年")
    d.text(x, d.y, "→「退職所得の源泉徴収票」も一緒に", 7.8, color=GRAY)
    d.y -= 14.5
    x = ML + 20
    x = d.check(x, "株・投資信託の売却益・配当", key="q6_stock")
    x = d.field(x, "", 40, key="q6_stock_v", unit="万円")
    d.text(x, d.y, "（特定口座「源泉徴収あり」・NISAで確定申告しない分は不要）", 7.8, color=GRAY)
    d.y -= 14.5
    x = ML + 20
    x = d.check(x, "商売・フリーランス・副業（業務委託・ネット販売など）", key="q6_biz")
    x = d.field(x, "売上", 40, key="q6_biz_s", unit="万円")
    x = d.field(x, "経費", 40, key="q6_biz_e", unit="万円")
    d.y -= 14.5
    x = ML + 20
    x = d.check(x, "家賃・地代（不動産の貸付け）", key="q6_rent")
    x = d.field(x, "収入", 40, key="q6_rent_s", unit="万円")
    x = d.field(x, "経費", 40, key="q6_rent_e", unit="万円")
    d.y -= 14.5
    x = ML + 32
    x = d.text(x, d.y, "商売・家賃がある方：青色申告を", 9.0) + 4
    x = d.radio(x, "している", key="q6_blue_yes", size=9.0)
    x = d.radio(x, "していない", key="q6_blue_no", size=9.0)
    x = d.radio(x, "わからない", key="q6_blue_unknown", size=9.0)
    d.text(x, d.y, "（分からなければ空欄で結構です）", 7.8, color=GRAY)
    d.y -= 14.5
    x = ML + 20
    x = d.check(x, "そのほか（暗号資産・FX・土地や建物の売却など。種類", key="q6_other")
    x = d.field(x, "", 90, key="q6_other_t")
    x = d.text(x - 8, d.y, "）", 9.5) + 3
    d.field(x, "", 40, key="q6_other_v", unit="万円")
    d.note("収入に入れないもの：失業手当・育児休業や病気の手当・児童手当・交通費・Q17の辞めた勤め先の給料。額面は、給料明細なら「総支給額」、年金なら「年金振込通知書」の年額です。", x=ML + 8)

    d.q("Q7", "障害者手帳などをお持ちですか（あなた自身のこと）。", kind="one")
    d.y -= 14
    x = ML + 8
    gate_line(d, x, "持っていない", "q7_no", "持っている", "q7_yes", "当てはまるもの全部に✓（手帳などのコピーも一緒に出してください）")
    d.y -= 15
    x = ML + 20
    x = d.check(x, "身体障害者手帳", key="q7_body")
    x = d.field(x, "", 24, key="q7_body_g", unit="級")
    x = d.check(x, "精神障害者保健福祉手帳", key="q7_mind")
    x = d.field(x, "", 24, key="q7_mind_g", unit="級")
    x = d.check(x, "療育手帳（記号：A・Bなど", key="q7_ryo")
    x = d.field(x - 4, "", 28, key="q7_ryo_g")
    d.text(x - 8, d.y, "）", 9.5)
    d.y -= 15
    x = ML + 20
    x = d.check(x, "市区町村の「障害者控除対象者認定書」", key="q7_nintei")
    x = d.check(x, "そのほか（寝たきり・戦傷病者手帳など：", key="q7_other")
    x = d.field(x - 4, "", 60, key="q7_other_t")
    d.text(x - 8, d.y, "）", 9.5)
    d.note("コピーは、氏名・等級・交付日が分かるページ。コピーを出していただければ、級などは空欄で結構です。"
           "手帳のことは、税金の「障害者控除」のためだけに聞いています（書かない場合は控除を受けられません）。ご家族の分（2・3ページ）は、ご本人に伝えたうえで書いてください。", x=ML + 8)

    d.q("Q8", "学校に通っていますか（高校・大学・大学院・専門学校など。夜間・通信制も含みます）。", kind="one")
    d.y -= 14
    x = ML + 8
    x = d.radio(x, "いいえ", key="q8_no")
    x = d.radio(x, "はい", key="q8_yes")
    x = d.arrow(x)
    d.field(x, "学校名", 220, key="q8_school")
    d.y -= 15
    x = ML + 24
    x = d.radio(x, "高校", key="q8_high")
    x = d.radio(x, "大学・短大・大学院・高専", key="q8_univ")
    x = d.radio(x, "専門学校・各種学校", key="q8_senmon")
    x = d.field(x, "入学した年月", 30, key="q8_in_y", unit="年")
    d.field(x - 4, "", 22, key="q8_in_m", unit="月")
    d.y -= 15
    x = ML + 24
    x = d.check(x, "今年中に卒業した・する", key="q8_grad")
    d.check(x, f"来年（{NEXT_YEAR}）3月に卒業予定", key="q8_grad_next")
    d.note("専門学校・各種学校・職業訓練校の方だけ、学校で「勤労学生控除の証明書」（在学証明）をもらって一緒に出してください。高校・大学などの方は要りません。", x=ML + 8)

    d.q("Q9", "12月31日に、結婚している相手（婚姻届を出している夫・妻）はいますか。", kind="one", star=True)
    d.y -= 14
    x = ML + 8
    x = d.radio(x, "いる", key="q9_yes")
    x = d.jump(x, "Aへ")
    x = d.radio(x, "いない", key="q9_no")
    x = d.jump(x, "Bへ")
    x = d.radio(x, "今年、夫・妻が亡くなった", key="q9_died")
    d.jump(x, "AとBの両方へ")
    d.y -= 15
    x = ML + 24
    x = d.text(x, d.y, "今年、結婚した・離婚した・夫や妻が亡くなった方", 9.5) + 6
    x = d.radio(x, "結婚", key="q9_marry")
    x = d.radio(x, "離婚", key="q9_div")
    x = d.radio(x, "亡くなった", key="q9_death")
    x = d.field(x, "いつ", 22, key="q9_when_m", unit="月")
    d.field(x - 4, "", 22, key="q9_when_d", unit="日")

    # ---- A
    d.y -= 8
    f = d.frame_begin("A　配偶者のこと（Q9で「いる」「亡くなった」の方だけ）")
    d.y -= 15
    x = ML + 10
    x = d.field(x, "お名前", 120, key="q9a_name")
    x = d.field(x, "フリガナ", 120, key="q9a_kana")
    x = d.radio(x, "夫", key="q9a_husband")
    x = d.radio(x, "妻", key="q9a_wife")
    d.y -= 16
    x = ML + 10
    x = d.text(x, d.y, "生年月日", 9.5) + 8
    x = birth(d, x, "q9a")
    d.y -= 16
    x = ML + 10
    x = d.text(x, d.y, "障害", 9.5) + 8
    x = d.radio(x, "ない", key="q9a_dis_no")
    x = d.radio(x, "ある（手帳の種類・等級。例：身体2級", key="q9a_dis_yes")
    x = d.field(x - 4, "", 110, key="q9a_dis_t")
    d.text(x - 8, d.y, "）→ 手帳のコピーも一緒に", 8.6)
    d.y -= 16
    x = ML + 10
    x = d.text(x, d.y, "住まい", 9.5) + 8
    x = d.radio(x, "一緒（入院中も「一緒」）", key="q9a_live_tog")
    x = d.radio(x, "別", key="q9a_live_sep")
    x = d.radio(x, "施設・老人ホーム", key="q9a_live_fac")
    x = d.radio(x, "外国（国名", key="q9a_live_abroad")
    x = d.field(x - 4, "", 60, key="q9a_country")
    d.text(x - 8, d.y, "）", 9.5)
    d.y -= 15
    x = ML + 10
    x = d.field(x, "別・施設・外国の方の住所", W - MR - x - 130, key="q9a_addr")
    d.y -= 15
    x = ML + 10
    x = d.text(x, d.y, "別・施設・外国の方：生活費を", 9.0) + 4
    x = d.radio(x, "送っている（今年の合計 約", key="q9a_send_yes", size=9.0)
    x = d.field(x - 4, "", 36, key="q9a_send_v", unit="万円）", size=9.0)
    x = d.radio(x, "送っていない", key="q9a_send_no", size=9.0)
    d.text(x - 4, d.y, "（外国：送金の記録も）", 7.8, color=GRAY)
    d.y -= 16
    x = ML + 10
    x = d.text(x, d.y, "今年の収入", 9.5) + 8
    x = d.radio(x, "ない", key="q9a_inc_no")
    x = d.radio(x, "わからない", key="q9a_inc_unknown")
    x = d.radio(x, "ある", key="q9a_inc_yes")
    x = d.arrow(x)
    d.text(x, d.y, "当てはまるもの全部に✓。額面で、12月分は見込みで", 9.0)
    d.y -= 15
    income_lines_person(d, "q9a", ML + 24)
    d.note("給料・パートは、1〜11月の給与明細の合計に12月の見込みを足して、1万円単位で。130万〜210万円くらいの方は、控除の額が5万円きざみで変わるので、"
           "なるべく正確に（源泉徴収票や12月の明細が出たら、勤め先に出してください）。遺族年金・障害年金・失業手当・育児休業や病気の手当は入れません。", x=ML + 10)
    d.y -= 14
    x = ML + 10
    x = d.text(x, d.y, "配偶者は、ご家族の商売（お店・農業など）の手伝いの給料をもらっていますか", 9.0) + 4
    x = d.radio(x, "いいえ", key="q9a_senju_no", size=9.0)
    x = d.radio(x, "はい", key="q9a_senju_yes", size=9.0)
    d.text(x - 6, d.y, "（会社勤めは「いいえ」）", 7.8, color=GRAY)
    d.frame_end(f)

    # ---- B
    f = d.frame_begin("B　結婚している相手がいない方（Q9で「いない」「亡くなった」の方だけ）")
    d.y -= 15
    x = ML + 10
    x = d.text(x, d.y, "1", 9.5, bold=True) + 6
    x = d.text(x, d.y, "当てはまるもの1つに✓", 9.0) + 8
    x = d.radio(x, "結婚したことがない", key="q9b_never")
    x = d.radio(x, "離婚した", key="q9b_div")
    x = d.radio(x, "死別した（行方不明を含む）", key="q9b_wid")
    d.y -= 15
    x = ML + 10
    yy = d.y
    d.y += 12.5
    d.para("住民票に「夫（未届）」「妻（未届）」と書かれている方はいますか（婚姻届を出していないパートナーのこと。ほとんどの方は「いない」です）",
           x=x + 12, size=9.0, leading=12.5)
    d.text(x, yy, "2", 9.5, bold=True)
    d.y -= 15
    x = ML + 24
    x = d.radio(x, "いない", key="q9b_cm_no")
    d.radio(x, "いる", key="q9b_cm_yes")
    d.frame_end(f)
    d.newpage()


def family_block(d: Form, n, p):
    f = d.frame_begin(None)
    d.y -= 15
    x = ML + 8
    x = d.text(x, d.y, n, 12.0, bold=True, color=BLUE) + 6
    x = d.field(x, "お名前", 110, key=f"{p}_name")
    x = d.field(x, "フリガナ", 110, key=f"{p}_kana")
    x = d.check(x, "今年亡くなった（", key=f"{p}_died")
    d.field(x - 10, "", 20, key=f"{p}_died_m", unit="月）")
    d.y -= 15.5
    x = ML + 22
    x = d.text(x, d.y, "続柄", 9.5) + 8
    for lab, k in [("子", "child"), ("孫", "gchild"), ("父", "father"), ("母", "mother"), ("祖父母", "gparent"),
                   ("兄弟姉妹", "sib"), ("配偶者の父母", "inlaw")]:
        x = d.radio(x, lab, key=f"{p}_rel_{k}")
    x = d.radio(x, "そのほか（", key=f"{p}_rel_other")
    x = d.field(x - 10, "", 45, key=f"{p}_rel_t")
    d.text(x - 8, d.y, "）", 9.5)
    d.y -= 15.5
    x = ML + 22
    x = d.text(x, d.y, "生年月日", 9.5) + 8
    x = birth(d, x, p, with_reiwa=True)
    d.y -= 15.5
    x = ML + 22
    x = d.text(x, d.y, "障害", 9.5) + 8
    x = d.radio(x, "ない", key=f"{p}_dis_no")
    x = d.radio(x, "ある（手帳の種類・等級。例：身体2級・療育A", key=f"{p}_dis_yes")
    x = d.field(x - 4, "", 90, key=f"{p}_dis_t")
    d.text(x - 8, d.y, "）→ コピーも一緒に", 8.6)
    d.y -= 15.5
    x = ML + 22
    x = d.text(x, d.y, "住まい", 9.5) + 8
    x = d.radio(x, "一緒（入院中も「一緒」）", key=f"{p}_live_tog")
    x = d.radio(x, "別", key=f"{p}_live_sep")
    x = d.radio(x, "施設・老人ホーム", key=f"{p}_live_fac")
    x = d.radio(x, "外国（国名", key=f"{p}_live_abroad")
    x = d.field(x - 4, "", 60, key=f"{p}_country")
    d.text(x - 8, d.y, "）", 9.5)
    d.y -= 15
    x = ML + 22
    x = d.field(x, "別・施設・外国の方の住所", W - MR - x - 120, key=f"{p}_addr")
    d.y -= 15
    x = ML + 22
    x = d.text(x, d.y, "別・施設・外国の方：生活費を", 9.0) + 4
    x = d.radio(x, "出している（今年の合計 約", key=f"{p}_send_yes", size=9.0)
    x = d.field(x - 4, "", 36, key=f"{p}_send_v", unit="万円）", size=9.0)
    x = d.radio(x, "出していない", key=f"{p}_send_no", size=9.0)
    d.check(x, "外国に留学中", key=f"{p}_study", size=9.0)
    d.y -= 15.5
    x = ML + 22
    x = d.text(x, d.y, "今年の収入", 9.5, bold=True) + 8
    x = d.radio(x, "ない", key=f"{p}_inc_no")
    x = d.radio(x, "わからない", key=f"{p}_inc_unknown")
    x = d.radio(x, "ある", key=f"{p}_inc_yes")
    x = d.arrow(x)
    x = d.check(x, "給料・アルバイト", key=f"{p}_inc_salary")
    x = d.field(x, "", 36, key=f"{p}_salary", unit="万円")
    x = d.check(x, "年金", key=f"{p}_inc_pension")
    x = d.field(x, "", 34, key=f"{p}_pension", unit="万円")
    d.y -= 15
    x = ML + 22
    x = d.check(x, "商売・業務委託", key=f"{p}_inc_biz", size=9.0)
    x = d.field(x, "収入", 24, key=f"{p}_biz_s", unit="万円", size=9.0)
    x = d.field(x, "経費", 24, key=f"{p}_biz_e", unit="万円", size=9.0)
    x = d.check(x, "退職金", key=f"{p}_inc_retire", size=9.0)
    x = d.field(x, "", 26, key=f"{p}_retire", unit="万円", size=9.0)
    x = d.check(x, "そのほか（", key=f"{p}_inc_other", size=9.0)
    x = d.field(x - 10, "", 30, key=f"{p}_other_t", size=9.0)
    x = d.text(x - 8, d.y, "）", 9.0) + 2
    d.field(x, "", 24, key=f"{p}_other_v", unit="万円", size=9.0)
    d.frame_end(f)
    d.y -= 1


def page3(d: Form):
    d.header("ご家族（配偶者のほか）")
    d.y -= 1
    d.text(ML, d.y - 10, "書く人（迷ったら書いてください。多い分には困りません）", 9.5, bold=True)
    d.y -= 11
    bullets = [
        "お子さん・お孫さんで、平成16年1月2日以後に生まれた方（22歳以下）は全員。小さいお子さんも、配偶者の扶養に入っている方も、収入がある方も（生命保険料の控除が増える判定にも使います）。",
        "そのほか、あなたが生活費を出している方や一緒に暮らしている方で、今年の収入（額面）が200万円くらいまでの方（23歳以上のお子さん・お孫さん、父母・祖父母・兄弟姉妹・配偶者の父母など。年金の方は年金の額で）。今年亡くなった方も。",
        "収入に入れないもの：遺族年金・障害年金・失業手当・育児休業や病気の手当・仕送り・交通費。株は、特定口座「源泉徴収あり」やNISAの分は入れません。健康保険の扶養（130万円・150万円）とは別のお話です。"
        "19〜22歳のお子さんのバイト代が130万〜200万円くらいの方は、1万円単位でなるべく正確に（控除の額が5万円きざみで変わります）。",
    ]
    for b in bullets:
        d.para("・" + b, size=8.5, leading=11.5, indent=8)
    d.y -= 14
    x = ML + 4
    x = d.text(x, d.y, "★", 10, color=RED) + 2
    x = d.text(x, d.y, "上の「書く人」に当てはまる方はいますか", 10.0, bold=True) + 8
    x = d.radio(x, "いない", key="fam_no", bold=True)
    x = d.jump(x, "4ページへ")
    x = d.radio(x, "いる", key="fam_yes", bold=True)
    d.jump(x, "下に1人ずつ（1人なら①だけ）")
    d.y -= 4
    family_block(d, "①", "f1")
    family_block(d, "②", "f2")
    family_block(d, "③", "f3")
    d.note("4人以上の方は、勤め先の方からこのページと6ページをもう1枚もらって、④⑤⑥として書いてください。書いていない方は「いない」ものとして申告書を作ります。")

    d.q("Q10", "①〜③（④〜も）の方で、ほかの方（配偶者など）の年末調整や確定申告で、税金の扶養に入っている方はいますか。", kind="one")
    d.y -= 14
    x = ML + 8
    x = d.radio(x, "いない", key="q10_no")
    x = d.radio(x, "わからない", key="q10_unknown")
    x = d.radio(x, "いる", key="q10_yes")
    x = d.arrow(x)
    x = d.field(x, "番号", 36, key="q10_num")
    x = d.text(x, d.y, "扶養に入れている人は", 9.5) + 4
    x = d.radio(x, "あなたの配偶者", key="q10_sp")
    d.radio(x, "ほかの方", key="q10_other")
    d.y -= 15
    x = ML + 24
    x = d.field(x, "「ほかの方」のお名前", 90, key="q10_who")
    x = d.field(x, "あなたから見て", 45, key="q10_rel")
    x = d.text(x, d.y, "住所", 9.5) + 4
    x = d.radio(x, "あなたと同じ", key="q10_addr_same")
    x = d.radio(x, "別（", key="q10_addr_diff")
    x = d.field(x - 10, "", 32, key="q10_addr")
    d.text(x - 8, d.y, "）", 9.5)

    d.q("Q11", "①〜③の方で、ご家族（あなた・配偶者・親など）の商売（お店・農業など）の手伝いの給料をもらっている方はいますか。", kind="one")
    d.y -= 14
    x = ML + 8
    x = d.radio(x, "いない", key="q11_no")
    x = d.radio(x, "わからない", key="q11_unknown")
    x = d.radio(x, "いる", key="q11_yes")
    x = d.arrow(x)
    d.field(x, "番号", 36, key="q11_num")
    d.note("外国に住んでいる方がいる場合は、①家族であることが分かる書類（出生証明書・戸籍など）と、②あなたからその方へ送金した記録（銀行や送金アプリの明細。家族1人ごとに、あなたの名前で送ったもの）"
           "を一緒に出してください（外国語のものは日本語訳も）。30歳〜69歳の方は、留学中（ビザなど留学が分かる書類も）・障害のある方・今年38万円以上送金した方だけが対象です。", x=ML + 8)
    d.newpage()


def page4(d: Form):
    d.header("払った保険料など")
    d.q("Q12", "今年、あなた自身が払った（12月までに払う）ものはありますか。", kind="one")
    d.note("（給料から引かれている健康保険・厚生年金・雇用保険は入れません。ご家族の口座や年金から引かれている分も入れません）", x=ML + 8)
    d.y -= 14
    x = ML + 8
    gate_line(d, x, "どれもない", "q12_no", "ある", "q12_yes", "当てはまるもの全部に✓", jump="5ページへ")
    items = [
        ("ア", "生命保険・医療保険・がん保険・介護医療保険・個人年金保険（保険会社に払うもの。はがきが届きます）", "q12_life", "▶ Q13へ"),
        ("イ", "地震保険（火災保険のはがきに「地震保険料」「旧長期損害保険料」とあるもの）", "q12_quake", "▶ Q14へ"),
        ("ウ", "国民年金・国民年金基金（ご家族の分をあなたが払った場合も）", "q12_kokunen", "（年金機構のはがきか領収書が必ず要ります）"),
        ("エ", "国民健康保険・後期高齢者医療・健康保険の任意継続・介護保険料（65歳以上が市区町村に払う分）", "q12_kokuho", "▶ Q15へ"),
        ("オ", "iDeCo（イデコ。自分の口座から払っている分）・小規模企業共済・心身障害者扶養共済（はがきが届きます）", "q12_ideco", ""),
    ]
    for lab, txt, key, tail in items:
        d.y -= 15
        x = ML + 20
        x = d.text(x, d.y, lab, 9.5, bold=True) + 5
        x = d.check(x, txt, key=key)
        if tail:
            d.text(x - 6, d.y, tail, 8.6, bold=tail.startswith("▶"), color=BLUE)
    d.note("届いた控除証明書（はがき）を、全部この用紙に留めてください。はがきの金額は書かなくて結構です（会計事務所が写します）。"
           "国民年金を2年分まとめて払った方は、Q20に「2年前納」と書いてください。", x=ML + 8)
    d.y -= 14
    x = ML + 8
    x = d.text(x, d.y, "はがきは", 9.5) + 6
    x = d.radio(x, "全部そろっている", key="q12_all_ok")
    x = d.radio(x, "まだ届いていないものがある（何の分", key="q12_missing")
    x = d.field(x - 4, "", 72, key="q12_missing_t")
    d.text(x - 8, d.y, "）→ 届いたらすぐに勤め先へ", 8.6)
    d.y -= 15
    x = ML + 8 + 46
    x = d.radio(x, "無くした（何の分", key="q12_lost")
    x = d.field(x - 4, "", 70, key="q12_lost_t")
    x = d.text(x - 8, d.y, "）→ 保険会社に再発行を", 8.6) + 8
    x = d.radio(x, "電子データで受け取った", key="q12_digital")
    d.text(x - 6, d.y, "→ 勤め先に相談", 8.6)
    d.note("（国民健康保険・介護保険などは、はがきが無くて結構です）", x=ML + 8)

    d.q("Q13", "生命保険・個人年金保険（Q12のアに✓の方。はがき1枚ごとに1行。5枚以上の方はQ20に「保険が○枚」と）")
    for i in range(1, 5):
        d.y -= 15
        x = ML + 8
        x = d.text(x, d.y, str(i), 9.5, bold=True) + 8
        x = d.field(x, "保険会社", 85, key=f"q13_{i}_co")
        x = d.radio(x, "生命・医療", key=f"q13_{i}_life")
        x = d.radio(x, "個人年金", key=f"q13_{i}_nenkin")
        x = d.field(x, "受取人", 75, key=f"q13_{i}_to")
        d.field(x, "あなたから見て", 34, key=f"q13_{i}_rel")
    d.note("受取人＝保険金や年金を受け取る方（保険証券や保険会社のマイページで分かります。分からなければ空欄で結構です）。「あなたから見て」は本人・妻・夫・子・母など。"
           "契約者がご家族でも、あなたのお金で払っているものは書けます（同じはがきを配偶者の年末調整でも使うことはできません）。", x=ML + 8)
    d.y -= 1
    d.para("★22歳以下のお子さん・お孫さんがいる方は、今年は生命保険料の控除が増えます（配偶者の扶養に入っているお子さんでも結構です）。"
           "3ページにお子さん全員を書いてあるか確かめてください。はがきのほかに書くことはありません。", x=ML + 8, size=8.4, leading=11.5, color=RED)

    d.q("Q14", "地震保険（Q12のイに✓の方。はがき1枚ごとに1行）")
    for i in range(1, 3):
        d.y -= 15
        x = ML + 8
        x = d.text(x, d.y, str(i), 9.5, bold=True) + 8
        x = d.field(x, "保険会社", 100, key=f"q14_{i}_co")
        x = d.text(x, d.y, "住んでいるのは", 9.0) + 4
        x = d.radio(x, "あなた", key=f"q14_{i}_self", size=9.0)
        x = d.radio(x, "ご家族（", key=f"q14_{i}_fam", size=9.0)
        x = d.field(x - 10, "", 45, key=f"q14_{i}_fam_t", size=9.0)
        x = d.text(x - 8, d.y, "）", 9.0) + 4
        d.radio(x, "人に貸している", key=f"q14_{i}_rent", size=9.0)
    d.note("「住んでいる」＝その家に住んでいる、または家財を使っている方。人に貸している家やお店の分は、控除になりません。", x=ML + 8)

    d.q("Q15", "国民健康保険などを自分で払った方（Q12のエに✓の方。だいたいで結構です）")
    for i in range(1, 3):
        d.y -= 15
        x = ML + 8
        x = d.text(x, d.y, str(i), 9.5, bold=True) + 8
        x = d.text(x, d.y, "だれの分", 9.5) + 4
        x = d.radio(x, "あなた", key=f"q15_{i}_self")
        x = d.radio(x, "ご家族（", key=f"q15_{i}_fam")
        x = d.field(x - 10, "", 30, key=f"q15_{i}_fam_t")
        x = d.text(x - 8, d.y, "）", 9.5) + 6
        x = d.text(x, d.y, "種類", 9.5) + 4
        x = d.radio(x, "国民健康保険", key=f"q15_{i}_kokuho", size=9.0)
        x = d.radio(x, "後期高齢者医療", key=f"q15_{i}_kouki", size=9.0)
        x = d.radio(x, "介護保険", key=f"q15_{i}_kaigo", size=9.0)
        d.radio(x, "任意継続", key=f"q15_{i}_nini", size=9.0)
        d.y -= 15
        x = ML + 24
        x = d.text(x, d.y, "払い方", 9.5) + 4
        x = d.radio(x, "納付書・口座振替", key=f"q15_{i}_pay_self", size=9.0)
        x = d.radio(x, "年金から引かれている（書けません）", key=f"q15_{i}_pay_pension", size=9.0)
        x += 2
        d.field(x, "今年1〜12月に払う額", 60, key=f"q15_{i}_amt", unit="円")
    d.note("12月分は見込みで。納付書・口座振替の通帳・市区町村の「納付額のお知らせ」などがあれば一緒に出してください。無ければ金額だけで結構です。", x=ML + 8)
    d.newpage()


def page5(d: Form):
    d.header("住宅ローン・前の勤め先・来年のこと・署名")
    d.q("Q16", "住宅ローン控除（家を買ったときのローンの税金の割引）を受けていますか。", kind="one")
    d.y -= 14
    x = ML + 8
    x = d.radio(x, "受けていない", key="q16_no")
    x = d.radio(x, "受けている（2年目以降）", key="q16_yes")
    x = d.jump(x, "下へ")
    x = d.radio(x, "今年が1年目", key="q16_first")
    d.radio(x, "わからない", key="q16_unknown")
    d.note("1年目の方：年末調整ではできません。来年2〜3月に確定申告をします（会計事務所からご案内します）。", x=ML + 8)
    d.y -= 2
    f = d.frame_begin("2年目以降の方")
    d.y -= 15
    x = ML + 10
    x = d.text(x, d.y, "住み始めた年", 9.5) + 6
    x = d.radio(x, "令和4年以前", key="q16_r4")
    x = d.radio(x, "令和5年以後（", key="q16_r5")
    x = d.field(x - 10, "", 40, key="q16_r5_y", unit="年）")
    d.y -= 15
    x = ML + 10
    x = d.text(x, d.y, "今年の12月31日にその家に", 9.5) + 6
    x = d.radio(x, "住んでいる", key="q16_live")
    d.radio(x, "転勤などで住んでいない", key="q16_notlive")
    d.y -= 15
    x = ML + 10
    x = d.text(x, d.y, "ローン", 9.5) + 6
    x = d.radio(x, "1本", key="q16_one")
    x = d.radio(x, "2本以上", key="q16_multi")
    x = d.radio(x, "今年借り換えた・完済した", key="q16_refi")
    d.y -= 15
    x = ML + 10
    x = d.text(x, d.y, "配偶者などと一緒に借りている（連帯債務）", 9.5) + 6
    x = d.radio(x, "いいえ", key="q16_joint_no")
    d.radio(x, "はい", key="q16_joint_yes")
    d.y -= 4
    d.para("出す書類：10〜11月ごろ税務署から届く「住宅借入金等特別控除申告書」（下半分が証明書になっている用紙。入居2年目に何年分かまとめて届いた方は今年の分）を、"
           "分かる欄だけ書いて（空欄でも結構です）この用紙に留めてください。税務署の用紙に「年末残高」が印字されている方は、それで結構です。"
           "印字されていない方は、銀行などから届く「年末残高等証明書」も必ず要ります（届いたらすぐに勤め先へ）。どちらも無い方はQ20に書いてください。計算は会計事務所がします。",
           x=ML + 10, size=8.4, leading=11.5)
    d.frame_end(f)

    d.q("Q17", "今年1月から今までに、給料をもらっていて、もう辞めた勤め先はありますか。", kind="one")
    d.note("（この勤め先に入る前の会社のほか、この勤め先と同時に勤めていて辞めた所も含みます。2社以上ある方はQ20にも書いてください）", x=ML + 8)
    d.y -= 14
    x = ML + 8
    x = d.radio(x, "ない", key="q17_no")
    x = d.radio(x, "ある", key="q17_yes")
    x = d.arrow(x)
    x = d.field(x, "会社名", 150, key="q17_co")
    x = d.field(x, "辞めた日", 26, key="q17_m", unit="月")
    d.field(x - 4, "", 26, key="q17_d", unit="日")
    d.y -= 15
    x = ML + 24
    x = d.text(x, d.y, "そこに「扶養控除等申告書」（家族のことを書く紙）を出していましたか", 9.0) + 6
    x = d.radio(x, "はい", key="q17_kou", size=9.0)
    x = d.radio(x, "いいえ・副業だった", key="q17_otsu", size=9.0)
    d.radio(x, "わからない", key="q17_unknown", size=9.0)
    d.y -= 15
    x = ML + 24
    x = d.text(x, d.y, "そこの「源泉徴収票」（辞めた後に届く、1年の給料と税金が書かれた紙）を", 9.0) + 6
    x = d.radio(x, "一緒に出す", key="q17_gensen_yes", size=9.0)
    d.radio(x, "まだもらっていない", key="q17_gensen_no", size=9.0)
    d.note("まだの方は、前の勤め先に「源泉徴収票をください」と頼んでください。12月の給料日までに届かないときは、来年ご自身の確定申告になります。"
           "退職金をもらった方は、2ページのQ6にも書いてください。", x=ML + 24)

    d.q("Q18", f"来年（{NEXT_YEAR}）、あなたやご家族のことで変わりそうなことはありますか。", kind="one")
    d.y -= 14
    x = ML + 8
    gate_line(d, x, "ない（家族も収入も今年と同じくらい）", "q18_no", "ある", "q18_yes", "当てはまるもの全部に✓")
    d.y -= 15
    x = ML + 20
    x = d.check(x, "出産の予定", key="q18_birth")
    x = d.check(x, "結婚・離婚の予定", key="q18_marry")
    x = d.check(x, "お子さんの就職・卒業", key="q18_job")
    d.check(x, "一緒に住む・別に住む", key="q18_live")
    d.y -= 15
    x = ML + 20
    x = d.check(x, "ご家族が外国へ行く・戻る", key="q18_abroad")
    x = d.check(x, "ご家族の収入が大きく変わる", key="q18_inc")
    x = d.arrow(x)
    x = d.field(x, "だれ", 44, key="q18_inc_who")
    x = d.field(x, "来年の見込み", 40, key="q18_inc_v", unit="万円")
    d.y -= 15
    x = ML + 20
    x = d.check(x, "そのほか", key="q18_other")
    d.field(x, "", W - MR - x - 4, key="q18_other_t")

    d.q("Q19", "この用紙と一緒に出すもの（写真の場合も、はがき1枚＝1枚と数えてください）", kind="one")
    d.y -= 14
    x = ML + 8
    gate_line(d, x, "何もない", "q19_no", "ある", "q19_yes", "当てはまるもの全部に✓を付けて、枚数を書いてください")
    d.y -= 15
    x = ML + 20
    x = d.check(x, "保険・年金のはがき・証明書", key="q19_hoken")
    x = d.field(x, "", 20, key="q19_hoken_n", unit="枚")
    x = d.check(x, "住宅ローンの書類", key="q19_loan")
    x = d.field(x, "", 20, key="q19_loan_n", unit="枚")
    x = d.check(x, "前の勤め先の源泉徴収票", key="q19_gensen")
    x = d.field(x, "", 20, key="q19_gensen_n", unit="枚")
    d.y -= 15
    x = ML + 20
    x = d.check(x, "国民健康保険などの領収書", key="q19_kokuho")
    x = d.field(x, "", 20, key="q19_kokuho_n", unit="枚")
    x = d.check(x, "障害者手帳などのコピー", key="q19_techo")
    x = d.field(x, "", 20, key="q19_techo_n", unit="枚")
    x = d.check(x, "学校の証明書", key="q19_school")
    x = d.field(x, "", 20, key="q19_school_n", unit="枚")
    d.y -= 15
    x = ML + 20
    x = d.check(x, "そのほか（外国の家族の書類・退職所得の源泉徴収票など）", key="q19_other")
    x = d.field(x, "", 100, key="q19_other_t")
    d.field(x, "", 22, key="q19_other_n", unit="枚")

    d.q("Q20", "会計事務所に伝えたいこと・聞きたいこと（マイナンバーは書かないでください）")
    d.lines(2, gap=15)

    d.y -= 4
    f = d.frame_begin("署名（確認と同意）", lw=1.4)
    d.para("（かんたんに言うと：この用紙をもとに、会計事務所が私の年末調整の申告書を作ることに同意します）", x=ML + 8, size=8.6, leading=12, color=GRAY)
    d.para("1 この用紙に書いたとおりに、勤め先と、勤め先が年末調整を頼んでいる税理士事務所が、下の申告書に書き写して作ることを承諾します。"
           "できあがった申告書は私が勤め先に提出するものです。内容に違うところがあれば申し出ます。", x=ML + 8, size=8.8, leading=12, indent=9)
    d.para("2 この用紙に書いた私と家族の情報（障害者手帳のことを含みます）を、年末調整と源泉徴収票・給与支払報告書の作成のために、"
           "勤め先と税理士事務所（守秘義務があります）が使うことに同意します。ほかの目的には使われません。", x=ML + 8, size=8.8, leading=12, indent=9)
    d.para("3 答えたことに変わりがあれば（結婚・出産・家族の収入が変わったなど）、12月31日までに、1ページの「出す先」の方に知らせます。",
           x=ML + 8, size=8.8, leading=12, indent=9)
    for s_ in [
        f"・{YEAR}分 給与所得者の扶養控除等（異動）申告書",
        f"・{YEAR}分 給与所得者の基礎控除申告書 兼 給与所得者の配偶者控除等申告書 兼 給与所得者の特定親族特別控除申告書 兼 所得金額調整控除申告書",
        f"・{YEAR}分 給与所得者の保険料控除申告書",
        f"・{YEAR}分 給与所得者の（特定増改築等）住宅借入金等特別控除申告書（住宅ローン控除2年目以降の方のみ。税務署から届いた用紙の空欄を補います）",
        f"・{NEXT_YEAR}分 給与所得者の扶養控除等（異動）申告書（市区町村へ出す給与所得者の扶養親族等申告書を兼ねます）",
    ]:
        d.para(s_, x=ML + 14, size=8.2, leading=11.0, indent=8)
    d.y -= 15
    x = ML + 8
    x = d.text(x, d.y, "書いた日", 9.5, bold=True) + 8
    x = d.text(x, d.y, f"{YEAR}", 9.5) + 4
    x = d.field(x, "", 26, key="sig_m", unit="月")
    x = d.field(x - 4, "", 26, key="sig_d", unit="日")
    x += 6
    x = d.text(x, d.y, "お名前（自筆）", 9.5, bold=True) + 2
    x = d.text(x, d.y, "★", 9.5, color=RED) + 4
    x = d.field(x, "", 150, key="sig_name", value_size=11)
    d.text(x - 6, d.y, "（印鑑は要りません）", 8.6, color=GRAY)
    d.frame_end(f)
    d.newpage()


def mn_row(d: Form, label, p, kind):
    """kind: 'self' | 'spouse' | 'family'"""
    d.y -= 19
    x = ML + 4
    d.text(x, d.y, label, 10.0, bold=True)
    x = ML + 62
    x = d.field(x, "お名前", 125, key=f"{p}_name")
    d.boxes(x + 2, 12, key=p)
    d.y -= 15
    x = ML + 62
    x = d.text(x, d.y, "書かない方は", 8.0, color=GRAY) + 4
    x = d.radio(x, "前に出した", key=f"{p}_before", size=9.0)
    x = d.radio(x, "まだ確認できない", key=f"{p}_unknown", size=9.0)
    if kind != "self":
        x = d.radio(x, "番号がない（外国在住など）", key=f"{p}_none", size=9.0)
        d.radio(x, "会計事務所が判断", key=f"{p}_office", size=9.0)
    d.y -= 3
    d.hr()


def page6(d: Form):
    d.header(None)
    d.y -= 20
    c = d.c
    c.setFillColor(black)
    c.rect(ML, d.y - 6, CW, 22, stroke=0, fill=1)
    d.text(ML + 8, d.y, "マイナンバー（別紙。必ず紙で出すか、専用フォルダへ。写真をLINE・メールで送らないでください）", 11.0, bold=True, color=white)
    d.y -= 8
    d.para("【使いみち】勤め先と、勤め先が年末調整を頼んでいる税理士事務所が、年末調整の申告書（扶養控除等申告書など。勤め先が保管します）・"
           "源泉徴収票（税務署へ）・給与支払報告書（市区町村へ）を作るためだけに使います。これ以外の目的には使いません。", size=8.8, leading=12.2)
    d.y -= 13
    x = ML + 4
    x = d.check(x, "（勤め先が✓します）健康保険・厚生年金・雇用保険の届出にも使います", key="emp_use_shaho", size=8.8)
    d.y -= 2
    d.para("【書き方】マイナンバーカードの裏・通知カード・「マイナンバー入り」で取った住民票を見て、1マスに1つずつ書いてください。"
           "前の年までに、この勤め先の年末調整の書類でその方の番号を出していて変わっていない方は、番号は書かずに「前に出した」に✓"
           "（健康保険などの手続きで出しただけの方や、今年初めて書くご家族は、番号を書いてください）。番号を書いた方は○に✓しないでください。", size=8.8, leading=12.2)
    d.y -= 2
    d.para("【だれの番号を書くか】あなた＝必ず。配偶者＝今年の収入が給料だけで207万円以下の方だけ。"
           "ご家族＝3ページに書いた方のうち、①16歳未満（平成23年1月2日以後生まれ）の方、②16歳以上で今年の収入が給料だけで136万円以下の方、"
           "③19〜22歳で197万円以下の方。それ以外の方と、Q10で「ほかの方の扶養に入っている」方は書かないでください。"
           "年金のある方など迷う方は「会計事務所が判断」に✓（必要なら後でお願いします）。", size=8.8, leading=12.2)
    d.y -= 4
    d.hr()
    mn_row(d, "あなた", "mn_self", "self")
    mn_row(d, "配偶者", "mn_sp", "spouse")
    mn_row(d, "ご家族①", "mn_f1", "family")
    mn_row(d, "ご家族②", "mn_f2", "family")
    mn_row(d, "ご家族③", "mn_f3", "family")
    if d.sample:
        d.y -= 10
        d.text(ML + 62, d.y, "※ 記入例の番号は架空です（実際は、カードの裏などの12桁を書きます）", 8.3, color=RED)
    d.note("・番号が分からない方：分かったら、この6ページだけを書いて勤め先に紙で渡してください（LINE・メール・メモでは送らないでください）。"
           "3ページをもう1枚書いた方は、このページももう1枚もらい、右上にお名前を書いて「④⑤⑥」と直して書いてください。")
    d.y -= 6
    f = d.frame_begin("勤め先が書く欄（本人の番号を新しく受け取ったときだけ。ご家族・配偶者の分の確認は要りません）", fill=LIGHT)
    d.y -= 15
    x = ML + 8
    x = d.text(x, d.y, "本人確認に使った書類", 9.5) + 6
    x = d.radio(x, "マイナンバーカード", key="emp_card", size=9.0)
    x = d.radio(x, "通知カード＋免許証など", key="emp_notice", size=9.0)
    d.radio(x, "番号入り住民票＋免許証など", key="emp_juminhyo", size=9.0)
    d.y -= 15
    x = ML + 8
    x = d.radio(x, "本人は「前に出した」→ 帳簿か前年の申告書に番号があることを確認した（本人確認は不要）", key="emp_same", size=9.0)
    d.y -= 15
    x = ML + 8
    x = d.field(x, "確かめた日", 110, key="emp_date")
    d.field(x, "確かめた人", 110, key="emp_by")
    d.note("このページは1〜5ページと分けて保管し、申告書・帳簿に番号を控えたら、鍵のかかる場所に保管するか裁断して捨ててください。"
           "写真は個人のLINE・メールで送らず、会計事務所が案内する専用フォルダへ。", x=ML + 8)
    d.frame_end(f)


def build(path, sample, title):
    d = Form(path, sample=sample, title=title)
    page1(d)
    page2(d)
    page3(d)
    page4(d)
    page5(d)
    page6(d)
    d.save()
    return d.page


def split_pdf(path, out_main, out_mn):
    """1〜5ページ（質問用紙）と6ページ（マイナンバー別紙）に分ける。"""
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        print("pypdf が無いため分割はスキップ")
        return
    r = PdfReader(path)
    w1, w2 = PdfWriter(), PdfWriter()
    for i, pg in enumerate(r.pages):
        (w2 if i == len(r.pages) - 1 else w1).add_page(pg)
    for w, o in ((w1, out_main), (w2, out_mn)):
        w.add_metadata({"/Title": os.path.splitext(os.path.basename(o))[0]})
        with open(o, "wb") as fh:
            w.write(fh)
        print(f"wrote {o}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--font-dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts"))
    ap.add_argument("--blank", action="store_true")
    ap.add_argument("--sample", action="store_true")
    a = ap.parse_args()
    register_fonts(a.font_dir)
    os.makedirs(a.out_dir, exist_ok=True)
    both = not (a.blank or a.sample)
    if a.blank or both:
        p = os.path.join(a.out_dir, f"{YEAR}分_年末調整の質問用紙.pdf")
        n = build(p, None, f"{YEAR}分 年末調整の質問用紙")
        print(f"wrote {p} ({n} pages)")
        split_pdf(p, os.path.join(a.out_dir, f"{YEAR}分_年末調整の質問用紙_1-5ページ.pdf"),
                  os.path.join(a.out_dir, f"{YEAR}分_年末調整の質問用紙_マイナンバー別紙.pdf"))
    if a.sample or both:
        p = os.path.join(a.out_dir, f"{YEAR}分_年末調整の質問用紙（記入例）.pdf")
        n = build(p, SAMPLE, f"{YEAR}分 年末調整の質問用紙（記入例）")
        print(f"wrote {p} ({n} pages)")


if __name__ == "__main__":
    main()
