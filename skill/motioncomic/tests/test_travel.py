import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "folder", "scripts"))
from build_travel import (PANEL_COLORS, detect_rects, frame_window, window_at,
                          wide_window, _filter, _seg_clip, AR)

PW, PH = 1200, 1600


def _synthetic_mask(path):
    """Pinta uma grade 2x3 com as PANEL_COLORS (ordem de leitura)."""
    import cv2
    import numpy as np
    img = np.full((PH, PW, 3), 255, np.uint8)
    cols, rows, gap = 2, 3, 14
    cw = (PW - gap) // cols
    ch = (PH - gap) // rows
    for k, (r, g, b) in enumerate(PANEL_COLORS):
        cx, cy = k % cols, k // cols
        x0, y0 = cx * (cw + gap), cy * (ch + gap)
        img[y0:y0 + ch, x0:x0 + cw] = (b, g, r)  # cv2 = BGR
    cv2.imwrite(path, img)
    return path


def _solid_page(path):
    import cv2
    import numpy as np
    img = np.full((PH, PW, 3), 40, np.uint8)
    img[200:600, 100:1100] = (60, 120, 200)
    cv2.imwrite(path, img)
    return path


def _probe(mp4):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", mp4],
        capture_output=True, text=True, check=True)
    return out.stdout.strip()


def test_detect_rects_reading_order(tmp="/tmp/_travel_mask.png"):
    _synthetic_mask(tmp)
    rects = detect_rects(tmp)
    assert len(rects) == 6, len(rects)
    # quadro1 esq-cima, quadro2 dir-cima => mesma faixa Y, X cresce
    assert rects[0][1] == rects[1][1]
    assert rects[1][0] > rects[0][0]
    # quadro3 (linha 2) abaixo do quadro1
    assert rects[2][1] > rects[0][1]


def test_frame_window_covers_and_16x9(tmp="/tmp/_travel_mask.png"):
    _synthetic_mask(tmp)
    for rect in detect_rects(tmp):
        cx, cy, cw = frame_window(rect, PW, PH)
        ch = cw / AR
        assert abs(cw / ch - AR) < 1e-6
        # janela contem o quadro
        assert cx - cw / 2 <= rect[0] + 1 and cx + cw / 2 >= rect[0] + rect[2] - 1
        # dentro da pagina
        assert cx - cw / 2 >= -1 and cx + cw / 2 <= PW + 1
        assert cy - ch / 2 >= -1 and cy + ch / 2 <= PH + 1


def test_window_at_endpoints_and_bump():
    a, b = (100, 100, 400), (900, 1400, 600)
    assert window_at(a, b, 0.0) == a
    assert window_at(a, b, 1.0) == b
    # com bump, no meio a camera afasta (cw maior que a media linear)
    mid = window_at(a, b, 0.5, bump=0.22)
    assert mid[2] > (a[2] + b[2]) / 2


def test_filter_string_has_crop_and_scale():
    vf = _filter((600, 800, 700), (300, 400, 500), 1.5, bump=0.2)
    assert "crop=" in vf and "scale=1280:720" in vf and "sin(PI*" in vf


def test_seg_clip_renders_16x9(tmp="/tmp/_travel_seg"):
    os.makedirs(tmp, exist_ok=True)
    page = _solid_page(os.path.join(tmp, "page.png"))
    out = os.path.join(tmp, "seg.mp4")
    a = frame_window((100, 200, 1000, 400), PW, PH)
    b = wide_window(PW, PH)
    _seg_clip(page, a, b, 0.5, out)
    assert os.path.exists(out)
    assert _probe(out) == "1280x720", _probe(out)


def test_filter_actually_crops_tight(tmp="/tmp/_travel_seg"):
    """Regressao: o crop precisa de fato APERTAR na janela, nao abrir pra
    in_w. (Bug: clip()/virgula escapada faziam o crop cair pra a pagina
    inteira; o scale final mascarava porque a saida fica 1280x720 igual.)
    Renderiza so o crop (sem scale) e confere a largura."""
    import subprocess
    os.makedirs(tmp, exist_ok=True)
    page = _solid_page(os.path.join(tmp, "page.png"))
    win = (600, 800, 700)  # janela parada de 700px num page de 1200
    crop_only = _filter(win, win, 0.5).split(",scale=")[0]
    frame = os.path.join(tmp, "crop.png")
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error",
                    "-framerate", "30", "-loop", "1", "-t", "0.5", "-i", page,
                    "-filter_complex", f"[0:v]{crop_only}[v]", "-map", "[v]",
                    "-ss", "0.2", "-frames:v", "1", frame], check=True)
    from png_size import png_size
    w, h = png_size(frame)
    assert abs(w - 700) <= 2, f"crop largura {w} != ~700 (caiu pra in_w?)"
    assert abs(w / h - AR) < 0.02, (w, h)


if __name__ == "__main__":
    test_detect_rects_reading_order()
    test_frame_window_covers_and_16x9()
    test_window_at_endpoints_and_bump()
    test_filter_string_has_crop_and_scale()
    test_seg_clip_renders_16x9()
    test_filter_actually_crops_tight()
    print("OK")
