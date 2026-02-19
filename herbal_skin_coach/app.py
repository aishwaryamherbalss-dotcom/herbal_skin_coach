# app.py — Aishwaryam Herbal Skin Coach (PRO FINAL — FULL PACKAGE + Option A Guide Overlay)
# ✅ Stable GoPro Engine (UNCHANGED scoring/reco logic)
# ✅ Front/Left/Right upload + Mobile Camera capture
# ✅ Auto Face Crop (default ON) + Selfie Mode tips (optional toggles)
# ✅ Eligibility checks (blur/brightness/resolution) + rescan guidance
# ✅ 10–15 sec visible progress bar + step messages
# ✅ ONE main recommendation + optional soap/toner/gel/weekly (Option 2)
# ✅ Better before/after (more realistic simulation) + highlighted overlay
# ✅ Spot marking circles (FACE-ONLY; avoids shirt marking)
# ✅ WhatsApp share (prefilled message) button
# ✅ Download Report PDF (IMPROVED attractive layout + spacing/alignment)
# ✅ History + Load Previous Report
# ✅ Reset / New Customer button
# ✅ “Rerun” behavior: Added explicit RERUN + RESET controls (Streamlit rerun-safe)
#
# ✅ NEW (Option A):
#    - After-capture / after-upload: shows an overlay guide (oval frame + left/right arrow)
#    - This is PREVIEW ONLY (does NOT change engine logic)
#
# Run:
#   pip install streamlit pillow numpy opencv-python reportlab
#   streamlit run app.py
import os, json, time, uuid, io, textwrap, hashlib
import re
import datetime as dt
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
# =========================
# GLOBAL SETTINGS
# =========================
SHOW_SECONDARY_RESET = False
import numpy as np
import streamlit as st

# -------------------------
# Session helpers (photos)
# -------------------------
def _img_key(pose_key: str) -> str:
    pose_key = (pose_key or "").strip().lower()
    if pose_key in ("front", "f"):
        return "front_img"
    if pose_key in ("left", "l"):
        return "left_img"
    if pose_key in ("right", "r"):
        return "right_img"
    # fallback: store raw by name
    return f"{pose_key}_img"

def set_image(pose_key: str, img):
    """Store captured PIL image in session_state under the expected keys."""
    k = _img_key(pose_key)
    st.session_state[k] = img

def get_image(pose_key: str):
    k = _img_key(pose_key)
    return st.session_state.get(k, None)

def clear_images():
    for k in ("front_img", "left_img", "right_img"):
        if k in st.session_state:
            del st.session_state[k]


from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageDraw
try:
    import cv2
    CV2_AVAILABLE = True
except Exception:
    CV2_AVAILABLE = False
# PDF (reportlab)
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False
# =========================
# CONFIG
# =========================
APP_NAME = "🍃 Aishwaryam Herbal Skin Coach (GoPro Stable Engine)"
INSTAGRAM_ID = "aishwaryam_herbals"
DATA_DIR = "data"
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
FOLLOWUPS_FILE = os.path.join(DATA_DIR, "followups.json")
SESSIONS_DIR = os.path.join(DATA_DIR, "sessions")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(SESSIONS_DIR, exist_ok=True)
st.set_page_config(page_title=APP_NAME, page_icon="🍃", layout="wide")
IMG_SMALL = 320
IMG_REPORT = 380
IMG_BA = 360
ENABLE_INSTAGRAM_UNLOCK = False  # kept off for now (live gating requires backend verification)
# =========================
# CSS
# =========================
st.markdown(
    """
    <style>
:root{--ah-green:#1F5D3B;--ah-leaf:#3A7D44;--ah-gold:#D4AF37;--ah-cream:#F7F3E9;}

      section.main > div { max-width: 1120px; }
      .ah-card {
        padding: 14px; border-radius: 14px;
        border: 1px solid #eee; background: #fff;
        box-shadow: 0 1px 10px rgba(0,0,0,0.03);
        margin-bottom: 10px;
      }
      .ah-mini { color: rgba(0,0,0,0.72); font-size: 0.92rem; }
      .ah-badge{display:inline-block;padding:6px 14px;border-radius:999px;font-weight:800;font-size:0.88rem;line-height:1.2;white-space:nowrap;letter-spacing:0.6px;}
      .streamlit-expanderHeader { font-weight: 600 !important; }
      .ah-overlay {
        position: relative;
        padding: 18px;
        border-radius: 14px;
        border: 1px solid #e9e9e9;
        background: linear-gradient(90deg,#f6fff4,#fff6f9);
      }
      .ah-hero {
        padding:14px;border-radius:14px;
        background:linear-gradient(90deg,#f6fff4,#fff6f9);
        border:1px solid #eee;
      }
      .ah-muted { color: rgba(0,0,0,0.65); }
    
      /* Brand buttons */
      div.stDownloadButton > button {
        background: var(--ah-gold) !important;
        color: #1F5D3B !important;
        border: 1px solid var(--ah-gold) !important;
        font-weight: 800 !important;
        border-radius: 12px !important;
        padding: 0.55rem 0.9rem !important;
      }
      div.stDownloadButton > button:hover { filter: brightness(0.97); }

      div.stLinkButton > a, div.stLinkButton > a:visited {
        background: var(--ah-green) !important;
        color: #ffffff !important;
        border: 1px solid var(--ah-green) !important;
        font-weight: 800 !important;
        border-radius: 12px !important;
        padding: 0.55rem 0.9rem !important;
        text-decoration: none !important;
        display: flex !important;
        justify-content: center !important;
      }
      div.stLinkButton > a:hover { filter: brightness(0.96); }

      div.stButton > button {
        border-radius: 12px !important;
        font-weight: 700 !important;
      }

    </style>
    """,
    unsafe_allow_html=True
)
# =========================
# HELPERS
# =========================

def vspace(px: int = 16):
    """Vertical spacing helper for clean layout (UI only)."""
    st.markdown(f"<div style='height:{int(px)}px'></div>", unsafe_allow_html=True)

def safe_rerun():
    """Rerun the app safely across Streamlit versions."""
    try:
        # Streamlit >= 1.18
        if hasattr(st, "rerun"):
            st.rerun()
            return
    except Exception:
        pass
    try:
        # Very old Streamlit
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
            return
    except Exception:
        pass
    # Last resort: do nothing (avoids crashing)
    st.session_state["_rerun_hint"] = str(uuid.uuid4())
    st.write(" ")
def load_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default
def save_json(path: str, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
def add_history(entry: Dict[str, Any]):
    hist = load_json(HISTORY_FILE, [])
    hist.insert(0, entry)
    save_json(HISTORY_FILE, hist[:200])
def add_followup(entry: Dict[str, Any]):
    """Append a follow-up entry to local followups.json (kept small like a mini CRM)."""
    e = dict(entry or {})
    e.setdefault("ts", datetime.now().isoformat(timespec="seconds"))
    e.setdefault("status", "open")
    fol = load_json(FOLLOWUPS_FILE, [])
    fol.insert(0, e)
    save_json(FOLLOWUPS_FILE, fol[:500])
def save_session_full(data: Dict[str, Any]):
    sid = data.get("session_id")
    if not sid:
        return
    path = os.path.join(SESSIONS_DIR, f"{sid}.json")
    save_json(path, data)
def load_session_full(session_id: str) -> Optional[Dict[str, Any]]:
    path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    if not os.path.exists(path):
        return None
    return load_json(path, None)
def resize_max(img: Image.Image, max_side: int = 1400) -> Image.Image:
    w, h = img.size
    m = max(w, h)
    if m <= max_side:
        return img
    scale = max_side / float(m)
    return img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
def pil_to_np(img: Image.Image) -> np.ndarray:
    return np.array(img.convert("RGB"))
def clamp01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))
def center_crop(arr: np.ndarray, pct: float = 0.72) -> np.ndarray:
    h, w = arr.shape[:2]
    ch, cw = int(h * pct), int(w * pct)
    y0 = (h - ch) // 2
    x0 = (w - cw) // 2
    return arr[y0:y0+ch, x0:x0+cw]
def crop_rect(arr: np.ndarray, x0: float, y0: float, x1: float, y1: float) -> np.ndarray:
    h, w = arr.shape[:2]
    xa = int(w * x0); xb = int(w * x1)
    ya = int(h * y0); yb = int(h * y1)
    xa = max(0, min(w-1, xa)); xb = max(1, min(w, xb))
    ya = max(0, min(h-1, ya)); yb = max(1, min(h, yb))
    return arr[ya:yb, xa:xb]
def disclaimer_text() -> str:
    return (
        "⚠️ **Cosmetic guidance only** (medical diagnosis illa).\n"
        "Patch test must. Severe acne/rash/pain na dermatologist consult pannunga.\n"
        "Lighting + angle affects result. Results vary person-to-person."
    )
def tanglish_headline(main: str) -> str:
    if main == "Clear Skin Herbal Serum":
        return "Aiyo okay 😄… pimple/oily touch theriyudhu. Don’t tension da — routine follow pannina improve aagum!"
    if main == "Kumkumadi Serum":
        return "Super da 👌… tan/pigmentation touch irukku. Common dhaan — steady routine panna glow semma varum!"
    if main == "Aloe Vera Hydrating Gel":
        return "Hmm… skin thirsty feel (dry/dehydrated) madiri 😅. No worry — hydration correct panna face soft-aa fresh-aa aagum!"
    return "Aww nice 😄… maintenance/glow mode. Simple routine podhum da!"
def one_line_hero(main: str) -> str:
    if main == "Clear Skin Herbal Serum":
        return "🔥 **Main hero:** Idhu dhaan pimple-control king/queen! Confusion venam — simple-ah follow pannunga."
    if main == "Kumkumadi Serum":
        return "✨ **Main hero:** Idhu dhaan pigmentation/tan glow hero. Slow-aa but steady-aa improvement varum."
    if main == "Aloe Vera Hydrating Gel":
        return "💧 **Main hero:** Hydration hero! Face calm-aa, soft-aa feel aagum."
    return "🌟 **Main hero:** Glow + maintenance hero! Daily/alternate night easy-aa podhum."
def method_standards_text() -> str:
    return (
        "### ✅ Method & Standards (How this works)\n"
        "- Multi-angle photo analysis (Front / Side averaging)\n"
        "- Brightness, shine, redness & tone variance estimation (image cues)\n"
        "- Spot cluster detection (non-medical, cosmetic estimate)\n"
        "- Combination evaluation: T-zone vs cheeks (estimate)\n"
        "- Photo quality eligibility control (blur/light/resolution checks)\n"
        "- Cosmetic guidance only (Not medical diagnosis)\n"
        "- Patch test + safety restrictions always shown\n"
        "\n"
        "**Process-standard note:** This is a documented, repeatable method (quality practice). "
        "It is not a clinical certification."
    )

# =========================
# DYNAMIC RESULT / EXPECTATION / GUIDELINES
# (Used in UI + PDF)
# =========================
def dynamic_report_guidance(goal: str, skin_type: str = "", concerns: Optional[list] = None) -> Dict[str, Any]:
    """Return dynamic (non-medical) result/expectation/guideline text based on goal.

    Keeps language simple + friendly; avoids pushing products.
    """
    g = (goal or "").strip().lower()
    stype = (skin_type or "").strip().lower()
    concerns = concerns or []

    # Defaults (safe, generic)
    result = [
        "Skin texture + brightness gradual-aa improve aagum.",
        "Routine consistent-aa follow pannina better stability varum.",
    ]
    expectation = [
        "Day 7: small visible change start aagum (feel + freshness).",
        "Day 14: tone/shine balance improve aagum.",
        "Day 21: base-level improvement stable-aa theriyum.",
        "If improvement slow-na, steps + usage check pannalam.",
    ]
    guidelines = [
        "Patch test compulsory (especially sensitive skin).",
        "Morning sunscreen use panna results fast-aa stabilize aagum.",
        "First 3 days slow-aa start; irritation na stop + simplify.",
        "Hydration + sleep + water — results-ku big support.",
    ]

    # Goal-specific tuning
    if any(k in g for k in ["glow", "bright", "brightening", "dull"]):
        result = [
            "Dullness reduce aagi face fresh + glow feel varum.",
            "Uneven tone konjam konjam even aagum.",
        ]
        expectation = [
            "Day 7: skin smooth + fresh feel.",
            "Day 14: visible brightness improve.",
            "Day 21: glow more stable-aa theriyum.",
            "Deep tan/pigmentation irundha extra time edukum.",
        ]
        guidelines = [
            "Morning sunscreen (SPF) — must. Tan/pigmentation avoid pannum.",
            "Harsh scrub avoid; gentle routine only.",
            "Night routine miss panna glow slow aagum — consistency important.",
        ] + guidelines[:1]

    elif any(k in g for k in ["acne", "pimple", "pimples", "spots"]):
        result = [
            "Redness + active bumps calm aagum.",
            "New breakouts frequency reduce aagum (with consistency).",
        ]
        expectation = [
            "Day 7: inflammation calm aagura feel.",
            "Day 14: new acne reduce aagum.",
            "Day 21: oil/flare control better-aagum.",
            "Severe acne / hormonal triggers irundha extra time + review needed.",
        ]
        guidelines = [
            "Active acne mela heavy oil / thick layers avoid.",
            "Pillow cover weekly change + face touch avoid.",
            "If burning/itching -> stop and do patch test again.",
        ] + guidelines[:1]

    elif any(k in g for k in ["pigment", "dark", "melasma"]):
        result = [
            "Uneven tone gradual-aa even aagum.",
            "Dark spots lightening slow but steady.",
        ]
        expectation = [
            "Day 7: texture/smoothness improve.",
            "Day 14: mild lightening start.",
            "Day 21: visible difference varum, but deep pigmentation-ku 4–8 weeks edukkalam.",
            "Sunscreen strict-aa illaina pigmentation comeback aagum.",
        ]
        guidelines = [
            "Sunscreen + shade habit — compulsory.",
            "Direct sun exposure avoid (especially 11–3).",
            "Harsh peel/scrub avoid; irritation pigmentation increase pannum.",
        ]

    elif any(k in g for k in ["tan", "tanning"]):
        result = [
            "Tan reduce aagi face brighter-aa theriyum.",
            "Tone more even + fresh look.",
        ]
        expectation = [
            "Day 7: mild tan reduction start.",
            "Day 14: more visible improvement.",
            "Day 21: base tan mostly settle aagum (depending on depth).",
        ]
        guidelines = [
            "Sunscreen + reapply — tan prevent.",
            "Outdoor after-care: wash + moisturize.",
        ] + guidelines[:1]

    elif any(k in g for k in ["anti", "aging", "wrinkle", "fine line"]):
        result = [
            "Skin firmness + smoothness improve aagum.",
            "Fine lines gradual-aa soften aagum.",
        ]
        expectation = [
            "Day 14: texture improvement noticeable.",
            "Day 21: glow + elasticity improve.",
            "Deep lines-ku 6–12 weeks consistent routine helps.",
        ]
        guidelines = [
            "Night routine consistency most important.",
            "Sunscreen is anti-aging hero.",
        ] + guidelines[:2]

    elif any(k in g for k in ["hydrate", "dry", "dryness"]):
        result = [
            "Dryness + tightness reduce aagum.",
            "Skin soft + plump feel varum.",
        ]
        expectation = [
            "Day 3–7: dryness comfort improve.",
            "Day 14: flaky areas reduce.",
            "Day 21: hydration stable-aagum.",
        ]
        guidelines = [
            "Hot water face wash avoid.",
            "Gentle cleanse only; over-washing dryness increase pannum.",
        ] + guidelines[:2]

    # Skin-type nuance
    if "oily" in stype or "combination" in stype:
        guidelines.append("Over-layering avoid; thin layers best for oily/combination skin.")
    if "sensitive" in stype:
        guidelines.append("Sensitive skin: 1 product at a time introduce pannunga.")

    return {
        "result": result,
        "expectation": expectation,
        "guidelines": guidelines,
    }
# =========================
# ACTIONS HELPERS (UI)
# =========================
def is_e164(phone: str) -> bool:
    """Basic E.164 validation: + followed by 8–15 digits."""
    return bool(re.fullmatch(r"\+\d{8,15}", (phone or "").strip()))
def goal_badge(goal: str) -> str:
    """Brand-styled goal badge (Aishwaryam Herbals: Herbal + Gold)."""
    g = (goal or "").strip().lower()
    # Text color accent per goal (kept subtle + premium)
    accents = {
        "glow": "#1F5D3B",
        "brightening": "#1F5D3B",
        "tan": "#8a4b2a",
        "tanning": "#8a4b2a",
        "pigmentation": "#5b247a",
        "dark spots": "#5b247a",
        "acne": "#8b1e2d",
        "pimples": "#8b1e2d",
        "anti aging": "#1f3a8a",
        "anti-aging": "#1f3a8a",
        "wrinkles": "#1f3a8a",
        "hydration": "#14532d",
        "dryness": "#14532d",
        "oil control": "#334155",
        "oily": "#334155",
        "sensitivity": "#7a1f4b",
        "sensitive": "#7a1f4b",
    }
    color = accents.get(g, "var(--ah-green)")
    label = (goal or "—").strip() or "—"
    # Cream background + gold border for premium look
    return (
        f"<span class='ah-badge' style='background:var(--ah-cream);"
        f"color:{color};border:2px solid var(--ah-gold);padding:6px 14px;'"
        f">✨ {label.upper()}</span>"
    )


# ---------------------------
# Smart Confirmation (mobile-friendly)
# ---------------------------

def _derive_skin_type_from_answers(oily: str, tight: str) -> str:
    """Return one of: oily, dry, combination, normal."""
    oily_yes = oily == "Yes"
    tight_yes = tight == "Yes"
    oily_no = oily == "No"
    tight_no = tight == "No"

    if oily_yes and tight_no:
        return "oily"
    if tight_yes and oily_no:
        return "dry"
    if oily_yes and tight_yes:
        return "combination"
    if oily_no and tight_no:
        return "normal"

    if oily_yes:
        return "oily"
    if tight_yes:
        return "dry"
    return "normal"


def refine_analysis_with_user_confirmation(
    data: dict,
    *,
    verdict: str,
    oily_by_noon: str | None = None,
    tight_after_wash: str | None = None,
    breakouts: str | None = None,
    manual_skin_type: str | None = None,
    manual_concerns: list[str] | None = None,
    manual_goal: str | None = None,
) -> dict:
    """Refine the existing analysis without breaking downstream logic."""
    refined = dict(data or {})
    refined["user_confirmation"] = {
        "verdict": verdict,
        "oily_by_noon": oily_by_noon,
        "tight_after_wash": tight_after_wash,
        "breakouts": breakouts,
        "manual_skin_type": manual_skin_type,
        "manual_concerns": manual_concerns,
        "manual_goal": manual_goal,
    }

    refined.setdefault("_original", {})
    refined["_original"].setdefault("skin_type", (data or {}).get("skin_type"))
    refined["_original"].setdefault("goal", (data or {}).get("goal"))

    scores = refined.get("scores") or {}

    conf = float(refined.get("confidence") or 0.6)
    if verdict == "No":
        conf = max(0.35, conf - 0.20)
    elif verdict == "Not sure":
        conf = max(0.45, conf - 0.10)
    refined["confidence"] = conf

    if manual_skin_type:
        refined["skin_type"] = manual_skin_type
        refined["skin_type_base"] = manual_skin_type

    if oily_by_noon and tight_after_wash and not manual_skin_type:
        refined_type = _derive_skin_type_from_answers(oily_by_noon, tight_after_wash)
        refined["skin_type"] = refined_type
        refined["skin_type_base"] = refined_type

    if manual_concerns is not None:
        refined["concerns"] = manual_concerns

    if manual_goal:
        refined["goal"] = manual_goal

    try:
        stype = refined.get("skin_type_base") or refined.get("skin_type")
        refined["main"] = decide_main_product(scores, stype)
        refined["addons"] = decide_addons(scores, stype)
    except Exception:
        pass

    return refined

def info_chips(data: Dict[str, Any]):
    """Small summary chips used in Actions section."""
    client = (data.get("client_name") or "Client").strip() or "Client"
    goal = (data.get("goal") or "—").strip()
    sid = (data.get("session_id") or "—")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"👤 <b>{client}</b>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"🎯 {goal_badge(goal)}", unsafe_allow_html=True)
    with c3:
        st.markdown(f"🧾 <span class='ah-badge' style='background:#eef2ff;color:#3730a3;border:1px solid rgba(0,0,0,0.08);'>{sid}</span>", unsafe_allow_html=True)
# =========================
# NEW (Option A) — Guide Overlay PREVIEW ONLY (does NOT affect analysis)
# =========================
def add_face_frame_overlay(img: Image.Image, mode: str) -> Image.Image:
    """
    mode: 'Front' | 'Left' | 'Right'
    Adds an oval frame + arrow/text hint as a preview after capture/upload.
    """
    im = resize_max(img.copy().convert("RGBA"), 900)
    W, H = im.size
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    # Slight dark overlay
    d.rectangle([0, 0, W, H], fill=(0, 0, 0, 55))
    # Oval frame
    oval_w = int(W * 0.56)
    oval_h = int(H * 0.74)
    cx, cy = int(W * 0.5), int(H * 0.48)
    x0, y0 = cx - oval_w // 2, cy - oval_h // 2
    x1, y1 = cx + oval_w // 2, cy + oval_h // 2
    # Border
    d.ellipse([x0, y0, x1, y1], outline=(0, 255, 0, 220), width=6)
    d.ellipse([x0 + 8, y0 + 8, x1 - 8, y1 - 8], outline=(255, 255, 255, 140), width=2)
    # Hint text
    hint = {
        "Front": "Face straight 😐 (Front)",
        "Left":  "Turn head LEFT ↩️ (Left side)",
        "Right": "Turn head RIGHT ↪️ (Right side)"
    }.get(mode, "Fit face inside frame")
    d.text((int(W * 0.05), int(H * 0.06)), hint, fill=(255, 255, 255, 235))
    d.text((int(W * 0.05), int(H * 0.10)), "Tip: Face fill ~70%, no filter, window light",
           fill=(255, 255, 255, 190))
    out = Image.alpha_composite(im, overlay).convert("RGB")
    return out
# =========================
# PRODUCTS
# =========================
@dataclass
class Product:
    name: str
    ptype: str
    purpose: str
    usage: str
    restrictions: str
    best_for: str
PRODUCTS: Dict[str, Product] = {
    "Clear Skin Herbal Serum": Product(
        "Clear Skin Herbal Serum", "Night Serum (Oil)",
        "Supports acne control, oil balance, black marks care (oily/acne-prone).",
        "2–3 drops night only. First 3 days alternate days → then daily if suits.",
        "Patch test. Avoid broken skin. Avoid during pregnancy. Don’t combine with strong chemical acne creams.",
        "Oily / acne-prone (support)"
    ),
    "24K Gold Serum": Product(
        "24K Gold Serum", "Glow Serum (Oil)",
        "Glow, firmness & maintenance care (clear skin maintenance).",
        "2 drops night (daily or alternate days).",
        "Avoid active acne. Patch test. Avoid during pregnancy.",
        "Maintenance / dull skin (support)"
    ),
    "Kumkumadi Serum": Product(
        "Kumkumadi Serum", "Ayurvedic Serum (Oil)",
        "Supports pigmentation/tan care + uneven tone care + glow.",
        "2–3 drops, night only (3–4 times/week).",
        "Not for active acne. Patch test. Avoid during pregnancy. Stop if irritation.",
        "Pigmentation / tan (support)"
    ),
    "Aloe Vera Hydrating Gel": Product(
        "Aloe Vera Hydrating Gel", "Gel",
        "Hydration + soothing + softness support.",
        "Small amount, morning & night.",
        "Patch test for sensitive skin.",
        "Dry / dehydrated feel (support)"
    ),
    "Papaya Brightening Gel": Product(
        "Papaya Brightening Gel", "Gel",
        "Mild brightening + gentle exfoliation support.",
        "Night preferred.",
        "Avoid broken/very sensitive skin. Patch test.",
        "Uneven tone / dullness (support)"
    ),
    "Red Wine Anti-Aging Gel": Product(
        "Red Wine Anti-Aging Gel", "Gel",
        "Antioxidant + glow support + early aging care support.",
        "Night preferred (face + neck).",
        "Patch test. Stop if irritation.",
        "Glow maintenance (support)"
    ),
    "Rose Toner": Product(
        "Rose Toner", "Toner",
        "Refresh + calm + prep step support.",
        "After cleansing, morning & night.",
        "Patch test if highly sensitive.",
        "All skin types"
    ),
    "Brightening Herbal Bath Powder": Product(
        "Brightening Herbal Bath Powder", "Ubtan (Face/Body)",
        "Tan/pigmentation support + glow support (weekly).",
        "Mix with water/rose water/milk/curd → 5–10 min → rinse.",
        "Patch test. Avoid broken/irritated skin.",
        "Tan/dullness weekly support"
    ),
    "Multani Mitti Powder": Product(
        "Multani Mitti Powder", "Face pack powder",
        "Oil control + deep cleansing support (weekly).",
        "Mix with rose water/water → apply → wash after semi-dry.",
        "Avoid overuse on dry/sensitive skin.",
        "Oily skin weekly support"
    ),
    "Charcoal Soap": Product(
        "Charcoal Soap", "Soap",
        "Deep cleansing + oil control support.",
        "Once daily (night best).",
        "Avoid overuse on dry/sensitive skin.",
        "Oily/acne-prone"
    ),
    "Neem Soap": Product(
        "Neem Soap", "Soap",
        "Purifying cleansing support, fresh feel.",
        "Daily use (face/body as needed).",
        "Patch test if sensitive.",
        "Oily/normal hygiene support"
    ),
    "Goat Milk Soap": Product(
        "Goat Milk Soap", "Soap",
        "Gentle cleansing + moisture support.",
        "Daily use.",
        "Patch test if allergy-prone.",
        "Normal/balanced"
    ),
    "Donkey Milk Soap": Product(
        "Donkey Milk Soap", "Soap",
        "Nourishing cleanse support for dry skin.",
        "Daily use.",
        "Patch test if sensitive.",
        "Dry/dehydrated"
    ),
}
def product_card(prod, badge: str = ""):
    """
    Accepts:
      - product name (str)
      - product dict with key 'name'
      - Product-like object with attribute .name
    Renders the same card style without crashing when prod is dict.
    """
    # normalize to product object/dict
    def _as_dict(p):
        if p is None:
            return {}
        if isinstance(p, dict):
            # allow both 'type' and 'ptype' keys
            d = dict(p)
            if "type" not in d and "ptype" in d:
                d["type"] = d.get("ptype")
            return d
        if isinstance(p, str):
            return {"name": p}

        # Support Product dataclass fields (ptype, purpose, best_for)
        d = {}
        if hasattr(p, "name"):
            d["name"] = getattr(p, "name")
        if hasattr(p, "ptype"):
            d["type"] = getattr(p, "ptype")
        if hasattr(p, "category"):
            d["category"] = getattr(p, "category")
        if hasattr(p, "purpose"):
            d["why"] = getattr(p, "purpose")
        if hasattr(p, "usage"):
            d["usage"] = getattr(p, "usage")
        if hasattr(p, "restrictions"):
            d["restrictions"] = getattr(p, "restrictions")
        if hasattr(p, "best_for"):
            d["best_for"] = getattr(p, "best_for")

        return d
    pd = _as_dict(prod)
    name = (pd.get("name") or "").strip()
    base = None
    if isinstance(PRODUCTS, dict) and name in PRODUCTS:
        base = PRODUCTS[name]
    # base may be Product object or dict
    if base is not None:
        if isinstance(base, dict):
            bd = dict(base)
        else:
            bd = _as_dict(base)
        bd.update(pd)
        pd = bd
    # Fallback display fields
    title = pd.get("name", "—")
    ptype = pd.get("type") or pd.get("category") or ""
    why = pd.get("why") or pd.get("purpose") or ""
    usage = pd.get("usage") or ""
    restr = pd.get("restrictions") or ""
    # If PRODUCTS stores Product objects with attributes, try to read them too
    if base is not None and not isinstance(base, dict):
        # attributes
        if hasattr(base, "why") and not why:
            why = getattr(base, "why")
        if hasattr(base, "usage") and not usage:
            usage = getattr(base, "usage")
        if hasattr(base, "restrictions") and not restr:
            restr = getattr(base, "restrictions")
        if hasattr(base, "type") and not ptype:
            ptype = getattr(base, "type")
    st.markdown(
        f"""
        <div class="ah-card">
          <h4 style="margin:0;">{title} {badge}</h4>
          <div class="ah-muted" style="margin-top:4px;">{ptype}</div>
          <div style="margin-top:10px;"><b>Why:</b> {why}</div>
          <div style="margin-top:6px;"><b>How to use:</b> {usage}</div>
          <div style="margin-top:6px;"><b>Note:</b> {restr}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    # =========================
    # AUTO FACE CROP (face-only scanning + avoid shirt marking)
    # =========================
def auto_crop_face(img: Image.Image, pad_ratio: float = 0.40) -> Tuple[Image.Image, Dict[str, Any]]:
    if not CV2_AVAILABLE:
        return img, {"ok": False, "reason": "opencv not available"}
    pil = resize_max(img.copy(), 1400).convert("RGB")
    arr = pil_to_np(pil)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    try:
        cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
        face_cascade = cv2.CascadeClassifier(cascade_path)
    except Exception:
        return pil, {"ok": False, "reason": "cascade load failed"}
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=5, minSize=(120, 120))
    if len(faces) == 0:
        return pil, {"ok": False, "reason": "no face detected"}
    x, y, w, h = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)[0]
    H, W = arr.shape[:2]
    pad_x = int(w * pad_ratio)
    pad_y = int(h * (pad_ratio + 0.10))
    x0 = max(0, x - pad_x)
    y0 = max(0, y - pad_y)
    x1 = min(W, x + w + pad_x)
    y1 = min(H, y + h + pad_y)
    crop = pil.crop((x0, y0, x1, y1))

    # If the crop becomes too small (common on mobile selfie / close-up),
    # expand it to keep enough pixels for quality checks & analysis.
    cw, ch = crop.size
    min_side = min(cw, ch)
    if min_side < 520:
        # Expand to a square-ish region around detected face
        cx = x + w // 2
        cy = y + h // 2
        target = max(720, int(max(w, h) * (1 + 2 * pad_ratio)))
        half = target // 2
        x0e = max(0, cx - half)
        y0e = max(0, cy - half)
        x1e = min(W, cx + half)
        y1e = min(H, cy + half)
        # If clamped too much, just use full image
        if (x1e - x0e) >= 320 and (y1e - y0e) >= 320:
            crop = pil.crop((x0e, y0e, x1e, y1e))
            x0, y0, x1, y1 = x0e, y0e, x1e, y1e
    meta = {
        "ok": True,
        "face_box": {"x": int(x), "y": int(y), "w": int(w), "h": int(h)},
        "crop": {"x0": int(x0), "y0": int(y0), "x1": int(x1), "y1": int(y1)},
    }
    return crop, meta
# =========================
# GUIDE IMAGES (cartoon-style)
# =========================
def make_pose_guide(kind: str, w: int = 520, h: int = 360) -> Image.Image:
    """
    Simple, clear photo guide cards (Front / Left / Right).
    Avoids confusing "arm-like" shapes by using minimal shapes only.
    """
    img = Image.new("RGB", (w, h), (255, 255, 255))
    d = ImageDraw.Draw(img)
    # Card background
    d.rounded_rectangle([10, 10, w-10, h-10], radius=22, outline=(230, 230, 230), width=2, fill=(250, 255, 249))
    # Title
    title = f"{kind} Photo Guide"
    d.text((24, 20), title, fill=(20, 20, 20))
    # Instructions
    d.text((24, 46), "Tip: Face fill ~70%, no filter, window light", fill=(90, 90, 90))
    d.text((24, 68), "Keep face inside green oval (no hair/neck/shirt)", fill=(90, 90, 90))
    # Face oval guide (analysis zone)
    oval = [int(w*0.18), int(h*0.22), int(w*0.56), int(h*0.86)]
    d.ellipse(oval, outline=(16, 185, 129), width=5)
    # Head position varies by kind
    cx = int(w*0.37)
    cy = int(h*0.55)
    face_w = int(w*0.22)
    face_h = int(h*0.46)
    if kind == "Front":
        fx = cx
        view_label = "Look straight"
        arrow = "•"
        profile = False
    elif kind == "Left":
        fx = cx - int(face_w*0.08)
        view_label = "Turn LEFT (side view)"
        arrow = "←"
        profile = True
    else:
        fx = cx + int(face_w*0.08)
        view_label = "Turn RIGHT (side view)"
        arrow = "→"
        profile = True
    # Head / face
    d.ellipse([fx-face_w//2, cy-face_h//2, fx+face_w//2, cy+face_h//2],
              fill=(255, 235, 215), outline=(210, 190, 175), width=2)
    # Hair cap (simple)
    d.pieslice([fx-face_w//2, cy-face_h//2-10, fx+face_w//2, cy-face_h//2+int(face_h*0.55)],
               start=180, end=360, fill=(70, 55, 45))
    d.rounded_rectangle([fx-face_w//2, cy-face_h//2+int(face_h*0.05), fx+face_w//2,
                         cy-face_h//2+int(face_h*0.18)], radius=18, fill=(70, 55, 45))
    # Facial features
    ey = cy - int(face_h*0.10)
    if not profile:
        # Two eyes for front
        eye_dx = int(face_w*0.20)
        d.ellipse([fx-eye_dx-10, ey-6, fx-eye_dx+10, ey+6], fill=(255,255,255), outline=(120,120,120))
        d.ellipse([fx+eye_dx-10, ey-6, fx+eye_dx+10, ey+6], fill=(255,255,255), outline=(120,120,120))
        d.ellipse([fx-eye_dx-3, ey-3, fx-eye_dx+3, ey+3], fill=(60,60,60))
        d.ellipse([fx+eye_dx-3, ey-3, fx+eye_dx+3, ey+3], fill=(60,60,60))
        # Nose center
        d.line([fx, cy-int(face_h*0.02), fx, cy+int(face_h*0.08)], fill=(170, 140, 120), width=2)
    else:
        # One eye + nose bump for side view
        eye_dx = int(face_w*0.10)
        d.ellipse([fx-eye_dx-10, ey-6, fx-eye_dx+10, ey+6], fill=(255,255,255), outline=(120,120,120))
        d.ellipse([fx-eye_dx-3, ey-3, fx-eye_dx+3, ey+3], fill=(60,60,60))
        # Nose bump towards direction
        if kind == "Left":
            nx = fx - int(face_w*0.18)
            d.polygon([(nx, cy), (nx+16, cy-10), (nx+16, cy+10)], fill=(255, 220, 200), outline=(210,190,175))
        else:
            nx = fx + int(face_w*0.18)
            d.polygon([(nx, cy), (nx-16, cy-10), (nx-16, cy+10)], fill=(255, 220, 200), outline=(210,190,175))
    # Smile
    d.arc([fx-int(face_w*0.18), cy+int(face_h*0.12), fx+int(face_w*0.18), cy+int(face_h*0.26)],
          start=20, end=160, fill=(160, 80, 85), width=3)
    # Label area on right
    d.rounded_rectangle([int(w*0.62), int(h*0.28), int(w*0.92), int(h*0.72)], radius=18,
                        outline=(210, 210, 210), width=2, fill=(255, 255, 255))
    d.text((int(w*0.65), int(h*0.33)), view_label, fill=(20, 20, 20))
    d.text((int(w*0.65), int(h*0.40)), f"Direction: {arrow}", fill=(16, 185, 129))
    return img
# =========================
# ELIGIBILITY
# =========================
def eligibility_check(img: Image.Image) -> Tuple[bool, List[str]]:
    """Return (eligible, issues).

    Goal: avoid rejecting decent mobile selfies while still protecting accuracy.

    Rules:
    - Low resolution is a warning unless extremely small.
    - Lighting is a warning unless extremely dark/overexposed.
    - Blur is a warning unless extremely blurry.
    """
    issues: List[str] = []
    blockers: List[str] = []
    warnings: List[str] = []

    # Normalize for checks (mobile camera_input is often ~640x480)
    img2 = resize_max(img, 1280)

    gray = ImageOps.grayscale(img2)
    arr = np.asarray(gray).astype(np.float32) / 255.0

    brightness = float(arr.mean())

    # Blur metric: variance of Laplacian
    lap_var: float = 0.0
    try:
        lap_var = float(cv2.Laplacian((arr * 255).astype(np.uint8), cv2.CV_64F).var())
    except Exception:
        lap_var = 0.0

    # --- Resolution (mostly warning)
    min_side = min(img2.size)
    # Treat low-res as warning unless extremely small.
    if min_side < 420:
        warnings.append("Low resolution. Clear photo upload pannunga (face fill ~70%).")
        if min_side < 220:
            blockers.append("Resolution romba kammi. Innum close/clear-a edunga.")

    # --- Lighting (mostly warning)
    if brightness < 0.30:
        warnings.append("Too dark. Window light front-la ninnu edunga.")
        if brightness < 0.20:
            blockers.append("Romba dark. Light improve pannunga.")
    if brightness > 0.92:
        warnings.append("Too bright / overexposed. Flash avoid pannunga.")
        if brightness > 0.97:
            blockers.append("Romba bright. Overexposed — retake pannunga.")

    # --- Blur (mobile tolerant)
    # On mobile, compression/auto HDR can reduce laplacian variance.
    if lap_var < 15:
        blockers.append("Blur/Shake romba irukku. Phone steady-ah pidichi tap-to-focus pannunga.")
    elif lap_var < 30:
        warnings.append("Slight blur. Steady + tap-to-focus panna accuracy better varum.")

    # Compose issues (show blockers first)
    issues.extend(blockers)
    issues.extend(warnings)

    eligible = (len(blockers) == 0)
    return eligible, issues

# =========================
# METRICS (ENGINE — UNCHANGED)
# =========================
def metric_brightness(arr: np.ndarray) -> float:
    return float(arr.mean() / 255.0)
def metric_redness(arr: np.ndarray) -> float:
    r = arr[:, :, 0].astype(np.float32)
    g = arr[:, :, 1].astype(np.float32)
    b = arr[:, :, 2].astype(np.float32)
    red = r - (g + b) / 2.0
    return float(np.clip(red.mean() / 255.0, -1, 1))
def metric_variance_gray(arr: np.ndarray) -> float:
    gray = arr.mean(axis=2).astype(np.float32) / 255.0
    return float(np.var(gray))
def metric_dark_ratio(arr: np.ndarray) -> float:
    gray = arr.mean(axis=2).astype(np.float32) / 255.0
    return float((gray < 0.35).mean())
def metric_shine(arr: np.ndarray) -> float:
    if CV2_AVAILABLE:
        hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)
        v = hsv[:, :, 2].astype(np.float32) / 255.0
        return float((v > 0.88).mean())
    gray = arr.mean(axis=2).astype(np.float32) / 255.0
    return float((gray > 0.86).mean())
def metric_texture_edges(arr: np.ndarray) -> float:
    if not CV2_AVAILABLE:
        gray = arr.mean(axis=2).astype(np.float32) / 255.0
        return float(np.var(gray))
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 60, 140)
    return float(edges.mean() / 255.0)
def metric_red_spots_count(arr: np.ndarray) -> int:
    if not CV2_AVAILABLE:
        r = arr[:, :, 0].astype(np.int32)
        g = arr[:, :, 1].astype(np.int32)
        b = arr[:, :, 2].astype(np.int32)
        redness = r - (g + b) // 2
        return int((redness > 35).sum() // 1800)
    img = cv2.GaussianBlur(arr, (7, 7), 0)
    r = img[:, :, 0].astype(np.int32)
    g = img[:, :, 1].astype(np.int32)
    b = img[:, :, 2].astype(np.int32)
    redness = r - (g + b) // 2
    mask = (redness > 40).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    spots = 0
    for c in cnts:
        area = cv2.contourArea(c)
        if 30 < area < 2200:
            spots += 1
    return spots
def compute_metrics_for_image(img: Image.Image) -> Dict[str, float]:
    img = resize_max(img, 1400)
    arr = center_crop(pil_to_np(img), 0.72)
    b = metric_brightness(arr)
    r = metric_redness(arr)
    v = metric_variance_gray(arr)
    d = metric_dark_ratio(arr)
    s = metric_shine(arr)
    t = metric_texture_edges(arr)
    spots = metric_red_spots_count(arr)
    v_n = clamp01(v / 0.05)
    t_n = clamp01(t / 0.20)
    spots_n = clamp01(spots / 18.0)
    return {
        "brightness": float(b),
        "redness": float(r),
        "redness_pos": float(max(0.0, r)),
        "variance": float(v),
        "variance_n": float(v_n),
        "dark_ratio": float(d),
        "shine": float(s),
        "texture": float(t),
        "texture_n": float(t_n),
        "spots": float(spots),
        "spots_n": float(spots_n),
    }
# =========================
# COMBINATION
# =========================
def combination_from_front(front_img: Optional[Image.Image]) -> Dict[str, Any]:
    if front_img is None:
        return {"ok": False, "is_combination": False, "note": "No front image provided."}
    img = resize_max(front_img, 1200)
    arr = pil_to_np(img)
    arr = center_crop(arr, 0.80)
    tzone = crop_rect(arr, 0.38, 0.20, 0.62, 0.85)
    cheek_l = crop_rect(arr, 0.12, 0.35, 0.32, 0.75)
    cheek_r = crop_rect(arr, 0.68, 0.35, 0.88, 0.75)
    t_shine = metric_shine(tzone)
    c_shine = float((metric_shine(cheek_l) + metric_shine(cheek_r)) / 2.0)
    diff = t_shine - c_shine
    is_combo = (t_shine >= 0.075) and (c_shine <= 0.045) and (diff >= 0.03)
    return {
        "ok": True,
        "is_combination": bool(is_combo),
        "tzone_shine": float(t_shine),
        "cheek_shine": float(c_shine),
        "diff": float(diff),
        "note": f"T-zone shine: {t_shine:.3f}, Cheek shine: {c_shine:.3f}, Diff: {diff:.3f}"
    }
# =========================
# SCORING (ENGINE — UNCHANGED)
# =========================
def stable_scores(avg: Dict[str, float]) -> Dict[str, float]:
    shine = avg["shine"]
    spots = avg["spots_n"]
    red = avg["redness_pos"]
    var = avg["variance_n"]
    dark = avg["dark_ratio"]
    bright = avg["brightness"]
    tex = avg["texture_n"]
    low_bright = clamp01((0.55 - bright) / 0.25)
    low_shine = clamp01((0.06 - shine) / 0.06)
    oily_score = clamp01(0.52*shine + 0.22*spots + 0.16*red + 0.10*tex)
    dry_score  = clamp01(0.55*low_bright + 0.25*tex + 0.20*low_shine)
    acne_score = clamp01(0.55*spots + 0.25*red + 0.20*oily_score)
    pigment_score = clamp01(0.62*var + 0.28*dark + 0.10*red)
    return {
        "oily_score": float(oily_score),
        "dry_score": float(dry_score),
        "acne_score": float(acne_score),
        "pigment_score": float(pigment_score),
    }
def decide_skin_type(scores: Dict[str, float]) -> str:
    oily = scores["oily_score"]
    dry = scores["dry_score"]
    if oily >= 0.58 and oily > dry + 0.08:
        return "Oily / Acne-prone"
    if dry >= 0.58 and dry > oily + 0.08:
        return "Dry / Dehydrated"
    return "Normal / Balanced"
def decide_main_product(scores: Dict[str, float], skin_type: str) -> Tuple[str, str]:
    acne = scores["acne_score"]
    pig = scores["pigment_score"]
    dry = scores["dry_score"]
    if acne >= 0.56:
        return "Clear Skin Herbal Serum", "acne"
    if pig >= 0.54:
        return "Kumkumadi Serum", "pigmentation"
    if dry >= 0.58:
        return "Aloe Vera Hydrating Gel", "dryness"
    return "24K Gold Serum", "glow"
def decide_addons(base_skin_type: str, main: str, scores: Dict[str, float], combo: bool) -> Dict[str, Optional[str]]:
    if base_skin_type == "Oily / Acne-prone":
        soap = "Charcoal Soap"
    elif base_skin_type == "Dry / Dehydrated":
        soap = "Donkey Milk Soap"
    else:
        soap = "Goat Milk Soap"
    toner = "Rose Toner"
    gel = None
    if main == "Kumkumadi Serum":
        gel = "Papaya Brightening Gel"
    elif main == "24K Gold Serum":
        gel = "Red Wine Anti-Aging Gel"
    elif main == "Clear Skin Herbal Serum":
        if scores["dry_score"] >= 0.45:
            gel = "Aloe Vera Hydrating Gel"
    if combo and main in ["Clear Skin Herbal Serum", "24K Gold Serum"]:
        gel = gel or "Aloe Vera Hydrating Gel"
    weekly = None
    if base_skin_type == "Oily / Acne-prone":
        weekly = "Multani Mitti Powder"
    elif scores["pigment_score"] >= 0.50:
        weekly = "Brightening Herbal Bath Powder"
    return {"soap": soap, "toner": toner, "gel": gel, "weekly": weekly}
def build_reasons(scores: Dict[str, float], photos_used: int, combo_info: Dict[str, Any]) -> List[str]:
    reasons = []
    if scores["oily_score"] >= 0.58:
        reasons.append("Shine/oil cues strong-aa irukku → oily tendency (estimate).")
    if scores["dry_score"] >= 0.58:
        reasons.append("Brightness low + texture cues → dry/dehydrated tendency (estimate).")
    if scores["acne_score"] >= 0.56:
        reasons.append("Red spot clusters + redness cues → acne/redness tendency (estimate).")
    if scores["pigment_score"] >= 0.54:
        reasons.append("Uneven tone variance + dark patch cues → pigmentation/tan tendency (estimate).")
    if photos_used < 2:
        reasons.append("Only 1 photo dhaan. 2–3 photos upload pannina stability/accuracy innum better-aa irukum.")
    else:
        reasons.append(f"{photos_used} photos average pannirukom → result more stable-aa varum.")
    if combo_info.get("ok") and combo_info.get("is_combination"):
        reasons.append("Front photo-la T-zone oilier + cheeks less shine → combination skin cue (estimate).")
    if not reasons:
        reasons.append("Overall cues balanced-aa theriyudhu → maintenance/glow focus.")
    return reasons
def compute_confidence(metrics_each: List[Dict[str, float]], scores: Dict[str, float], combo_info: Dict[str, Any]) -> float:
    n = len(metrics_each)
    base = 0.48
    base += 0.00 if n == 1 else (0.14 if n == 2 else 0.22)
    max_score = max(scores.values())
    base += 0.10 if max_score >= 0.72 else (0.06 if max_score >= 0.60 else 0.02)
    br = [m["brightness"] for m in metrics_each]
    br_std = float(np.std(br)) if len(br) > 1 else 0.0
    if n >= 2:
        base += 0.08 if br_std < 0.05 else (0.04 if br_std < 0.08 else -0.06)
    if scores["oily_score"] >= 0.58 and scores["dry_score"] >= 0.58:
        base -= 0.06
    if combo_info.get("ok") and combo_info.get("is_combination"):
        base += 0.03
    return float(np.clip(base, 0.25, 0.92))
def analyze_photos(front: Optional[Image.Image], left: Optional[Image.Image], right: Optional[Image.Image]) -> Dict[str, Any]:
    imgs, labels = [], []
    if front is not None:
        imgs.append(front); labels.append("Front")
    if left is not None:
        imgs.append(left); labels.append("Left")
    if right is not None:
        imgs.append(right); labels.append("Right")
    if not imgs:
        return {"ok": False, "error": "No photos uploaded."}
    metrics_each = [compute_metrics_for_image(im) for im in imgs]
    keys = metrics_each[0].keys()
    avg = {k: float(np.mean([m[k] for m in metrics_each])) for k in keys}
    scores = stable_scores(avg)
    base_skin_type = decide_skin_type(scores)
    main, goal = decide_main_product(scores, base_skin_type)
    combo_info = combination_from_front(front)
    is_combo = bool(combo_info.get("is_combination", False))
    final_skin_type = base_skin_type
    if is_combo and base_skin_type in ["Normal / Balanced", "Oily / Acne-prone"]:
        final_skin_type = "Combination (Oily T-zone + Normal/Dry Cheeks)"
    addons = decide_addons(base_skin_type, main, scores, combo=is_combo)
    reasons = build_reasons(scores, photos_used=len(imgs), combo_info=combo_info)
    conf = compute_confidence(metrics_each, scores, combo_info=combo_info)
    concerns = []
    if scores["acne_score"] >= 0.50:
        concerns.append("Acne / redness (estimate)")
    if scores["pigment_score"] >= 0.50:
        concerns.append("Pigmentation / tanning (estimate)")
    if base_skin_type == "Dry / Dehydrated":
        concerns.append("Dryness / dullness (estimate)")
    if is_combo:
        concerns.append("Combination balance (estimate)")
    if not concerns:
        concerns.append("Maintenance / glow (estimate)")
    return {
        "ok": True,
        "photos_used": len(imgs),
        "photo_labels": labels,
        "avg_metrics": avg,
        "scores": scores,
        "skin_type_base": base_skin_type,
        "skin_type": final_skin_type,
        "concerns": concerns,
        "confidence": conf,
        "reasons": reasons,
        "main_product": main,
        "goal": goal,
        "addons": addons,
        "combo_info": combo_info,
    }
# =========================
# SIMULATION (before/after) — improved realism (ONLY simulation)
# =========================
def simulate_after_realistic(img: Image.Image, goal: str) -> Image.Image:
    x = resize_max(img.copy(), 1100).convert("RGB")
    arr = pil_to_np(x)
    if CV2_AVAILABLE:
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        smooth = cv2.bilateralFilter(bgr, d=9, sigmaColor=60, sigmaSpace=60)
        ycrcb = cv2.cvtColor(smooth, cv2.COLOR_BGR2YCrCb).astype(np.float32)
        Y, Cr, Cb = cv2.split(ycrcb)
        Y = np.clip(Y * 1.04 + 2, 0, 255)
        if goal == "acne":
            Cr = np.clip(Cr * 0.985, 0, 255)
        elif goal == "pigmentation":
            Y = np.clip(Y * 1.02, 0, 255)
        elif goal == "dryness":
            Y = np.clip(Y * 1.05 + 3, 0, 255)
        else:
            Y = np.clip(Y * 1.03 + 2, 0, 255)
        out = cv2.merge([Y, Cr, Cb]).astype(np.uint8)
        out = cv2.cvtColor(out, cv2.COLOR_YCrCb2BGR)
        hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV).astype(np.float32)
        Hh, Ss, Vv = cv2.split(hsv)
        Ss = np.clip(Ss * 1.05, 0, 255)
        hsv2 = cv2.merge([Hh, Ss, Vv]).astype(np.uint8)
        out2 = cv2.cvtColor(hsv2, cv2.COLOR_HSV2BGR)
        rgb = cv2.cvtColor(out2, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)
    x = x.filter(ImageFilter.SMOOTH_MORE)
    x = ImageEnhance.Contrast(x).enhance(1.02)
    x = ImageEnhance.Brightness(x).enhance(1.03)
    if goal == "acne":
        r, g, b = x.split()
        r = r.point(lambda v: int(v * 0.985))
        x = Image.merge("RGB", (r, g, b))
    elif goal == "pigmentation":
        x = ImageEnhance.Brightness(x).enhance(1.04)
    elif goal == "dryness":
        x = ImageEnhance.Brightness(x).enhance(1.05)
    return x
def highlight_changes(before: Image.Image, after: Image.Image) -> Image.Image:
    b = resize_max(before.copy(), 900).convert("RGB")
    a = resize_max(after.copy(), 900).convert("RGB")
    if b.size != a.size:
        a = a.resize(b.size, Image.LANCZOS)
    b_np = pil_to_np(b).astype(np.int16)
    a_np = pil_to_np(a).astype(np.int16)
    diff = np.abs(a_np - b_np).mean(axis=2).astype(np.float32)
    if float(diff.max()) < 1e-6:
        diff = diff + 1.0
    diff = (diff / diff.max() * 255.0).astype(np.uint8)
    if CV2_AVAILABLE:
        heat = cv2.applyColorMap(diff, cv2.COLORMAP_JET)
        heat = cv2.cvtColor(heat, cv2.COLOR_BGR2RGB)
        heat_img = Image.fromarray(heat)
        return Image.blend(b, heat_img, alpha=0.34)
    heat_img = ImageOps.colorize(Image.fromarray(diff), black="#000000", white="#ff3b3b").convert("RGB")
    return Image.blend(b, heat_img, alpha=0.30)
# =========================
# SPOT MARKING — FACE ONLY
# =========================
def detect_spots_and_draw_circles_face_only(face_img: Image.Image) -> Tuple[Image.Image, int]:
    base = resize_max(face_img.copy(), 900).convert("RGB")
    arr = pil_to_np(base)
    if not CV2_AVAILABLE:
        return base, 0
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    blur = cv2.GaussianBlur(bgr, (7, 7), 0)
    rgb = cv2.cvtColor(blur, cv2.COLOR_BGR2RGB).astype(np.int32)
    r = rgb[:, :, 0]; g = rgb[:, :, 1]; b = rgb[:, :, 2]
    redness = r - ((g + b) // 2)
    mask = (redness > 40).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, np.ones((3, 3), np.uint8), iterations=1)
    # Ignore only the OUTER BORDER to reduce hair/background false positives
    H, W = mask.shape[:2]
    margin = int(min(H, W) * 0.06)  # 6% border only (NO nose/cheek center ignored)
    mask[:margin, :] = 0
    mask[-margin:, :] = 0
    mask[:, :margin] = 0
    mask[:, -margin:] = 0
    # Extra safety: ignore common non-face areas (neck/shirt edges) inside the crop.
    # We keep a central ellipse (cheeks/forehead) and remove the bottom band.
    H, W = mask.shape[:2]
    ellipse = np.zeros((H, W), dtype=np.uint8)
    center = (int(W * 0.50), int(H * 0.45))
    axes = (max(1, int(W * 0.42)), max(1, int(H * 0.46)))
    cv2.ellipse(ellipse, center, axes, 0, 0, 360, 255, -1)
    mask = cv2.bitwise_and(mask, ellipse)
    mask[int(H * 0.85):, :] = 0
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    circles = 0
    for c in cnts:
        area = cv2.contourArea(c)
        if 30 < area < 1800:
            (x, y), radius = cv2.minEnclosingCircle(c)
            radius = int(max(6, min(radius, 35)))
            cv2.circle(bgr, (int(x), int(y)), radius, (0, 255, 0), 2)
            circles += 1
    out = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    return Image.fromarray(out), circles
# =========================
# WHATSAPP
# =========================
def whatsapp_link(phone_e164: str, message: str) -> str:
    import urllib.parse
    msg = urllib.parse.quote(message)
    phone = phone_e164.replace(" ", "")
    return f"https://wa.me/{phone.lstrip('+')}?text={msg}"
def build_whatsapp_report_message(data: Dict[str, Any]) -> str:
    addons = data["addons"]
    who = (data.get("client_name") or "").strip()
    ref = (data.get("client_ref") or "").strip()
    head = f"Client: {who}\nRef: {ref}\n" if (who or ref) else ""
    msg = (
        "Hi Aishwaryam Herbals 👋\n"
        f"{head}"
        "I used Herbal Skin Coach.\n"
        f"Skin type (estimate): {data['skin_type']}\n"
        f"Confidence: {int(float(data['confidence'])*100)}%\n"
        f"Main recommendation: {data['main_product']}\n"
        f"Optional: Soap={addons['soap']} | Toner={addons['toner']}"
        + (f" | Gel={addons['gel']}" if addons.get("gel") else "")
        + (f" | Weekly={addons['weekly']}" if addons.get("weekly") else "")
        + "\nPlease guide me for purchase & delivery.\n"
    )
    return msg
# =========================
# PDF — ATTRACTIVE LAYOUT (LOCKED FINAL)
# =========================
def _pdf_wrap_lines(txt: str, width: int) -> List[str]:
    return textwrap.wrap(txt, width=width, break_long_words=False, replace_whitespace=False)
def make_report_pdf_bytes_attractive(
    data: Dict[str, Any],
    face_before: Optional[Image.Image],
    face_after: Optional[Image.Image],
    brand_name: str = "Aishwaryam Herbals",
    instagram: str = "@aishwaryam_herbals",
    highlight: Optional[Any] = None,
) -> bytes:
    """
    Attractive, print-friendly PDF report.
    - Stable HERO mapping (never shows —)
    - Better spacing + colored section headers
    - Option 2 Professional: supporting (soap/toner/gel) + weekly add-on selected dynamically
    NOTE: Does NOT change scoring / recommendation logic. Only report presentation + add-ons selection.
    """
    import io
    from datetime import datetime
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    # ---------- Helpers ----------
    def _as_prod_dict(p: Any) -> Dict[str, Any]:
        """Normalize Product/object/dict to a dict used by PDF renderer."""
        if p is None:
            return {}
        if isinstance(p, dict):
            d = dict(p)
            # allow both 'type' and 'ptype'
            if "type" not in d and "ptype" in d:
                d["type"] = d.get("ptype")
            # allow 'why' from 'purpose'
            if "why" not in d and "purpose" in d:
                d["why"] = d.get("purpose")
            return d
        if isinstance(p, str):
            return {"name": p}

        d: Dict[str, Any] = {}

        if hasattr(p, "name"):
            d["name"] = getattr(p, "name")
        if hasattr(p, "ptype"):
            d["type"] = getattr(p, "ptype")
        elif hasattr(p, "type"):
            d["type"] = getattr(p, "type")
        if hasattr(p, "category"):
            d["category"] = getattr(p, "category")
        if hasattr(p, "usage"):
            d["usage"] = getattr(p, "usage")
        if hasattr(p, "restrictions"):
            d["restrictions"] = getattr(p, "restrictions")

        # Purpose → why (used in PDF)
        if hasattr(p, "purpose"):
            d["why"] = getattr(p, "purpose")
        elif hasattr(p, "why"):
            d["why"] = getattr(p, "why")

        return d

    def _resolve_product(p_any: Any) -> Dict[str, Any]:
        p = _as_prod_dict(p_any)
        name = (p.get("name") or "").strip()
        if name and isinstance(PRODUCTS, dict) and name in PRODUCTS:
            base = _as_prod_dict(PRODUCTS[name])
            base.update(p)
            return base
        return p
    def _pick_by_name(fallback_name: str) -> Dict[str, Any]:
        if isinstance(PRODUCTS, dict) and fallback_name in PRODUCTS:
            return _as_prod_dict(PRODUCTS[fallback_name])
        return {"name": fallback_name}
    # ---------- Timestamp used everywhere ----------
    ts = datetime.now()
    ts_str = ts.strftime("%d %b %Y • %I:%M %p")
    # ---------- HERO mapping (source of truth: main_product) ----------
    hero_any = data.get("main_product") or data.get("hero") or data.get("recommendation") or data.get("selected_product")
    hero = _resolve_product(hero_any)
    # Hard fallback so PDF never shows —
    if not (hero.get("name") or "").strip():
        hero = _pick_by_name("24K Gold Serum")
    # Ensure fields exist
    hero.setdefault("type", hero.get("category") or "Serum")
    hero.setdefault("why", hero.get("purpose", "") or "Ungal skin-ku glow + support pannum.")
    hero.setdefault("usage", "2 drops night (daily / alternate days).")
    hero.setdefault("restrictions", "Patch test. Avoid broken skin. If irritation stop.")
    data["hero"] = hero  # keep consistent
    # ---------- Build concerns / skin type text ----------
    concerns = data.get("concerns") or []
    skin_type = str(data.get("skin_type") or "").strip()
    concerns_text = " ".join([str(c).lower() for c in concerns])
    skin_type_l = skin_type.lower()
    # ---------- Option 2 Professional: multi-layer add-ons ----------
    # Priority (primary) from concerns/skin type (we don't override HERO)
    if any(k in concerns_text for k in ["pigment", "tan", "dark", "uneven", "spots"]):
        primary = "pigment"
    elif any(k in concerns_text for k in ["acne", "pimple", "pimples", "breakout", "blackhead", "whitehead"]):
        primary = "acne"
    elif any(k in concerns_text for k in ["wrinkle", "aging", "antiaging", "fine line", "firm", "firmness"]):
        primary = "aging"
    elif "oily" in skin_type_l:
        primary = "oil"
    elif "dry" in skin_type_l:
        primary = "dry"
    else:
        primary = "maintenance"
    # SOAP selection (skin type + acne + pigment)
    if any(k in concerns_text for k in ["acne", "pimple", "pimples", "breakout"]):
        soap = _pick_by_name("Neem Soap")
    elif "oily" in skin_type_l:
        soap = _pick_by_name("Charcoal Soap")
    elif "dry" in skin_type_l:
        soap = _pick_by_name("Goat Milk Soap")
    elif any(k in concerns_text for k in ["pigment", "tan", "spots", "dark"]):
        soap = _pick_by_name("Manjistha Soap")
    elif "dull" in concerns_text:
        soap = _pick_by_name("Papaya Soap")
    else:
        soap = _pick_by_name("Goat Milk Soap")
    # TONER selection
    if "dry" in skin_type_l:
        toner = _pick_by_name("Rose Water")
    else:
        toner = _pick_by_name("Rose Toner")
    # GEL selection (secondary support using primary)
    if primary == "aging":
        gel = _pick_by_name("Red Wine Anti-Aging Gel")
    elif primary == "pigment":
        gel = _pick_by_name("Papaya Brightening Gel")
    else:
        gel = _pick_by_name("Aloe Vera Hydrating Gel")
  # ---------- Weekly add-on selection (dynamic + always prints product name) ----------
    weekly_freq = "1x/week"
    weekly_reason = "Maintenance + glow keep panna help pannum."
    if primary == "pigment":
        weekly = _pick_by_name("Brightening Herbal Bath Powder")
        weekly_reason = "Tan/pigmentation reduce panna strong support."
    elif primary == "acne":
        weekly = _pick_by_name("All-in-One Gentle Herbal Peel Mask")
        weekly_reason = "Pores clean + acne control support."
    elif primary == "oil":
        weekly = _pick_by_name("Multani Mitti Powder")
        weekly_reason = "Oil balance panna help pannum."
    elif primary == "dry":
        weekly = _pick_by_name("Aloe Vera Hydrating Gel")
        weekly_freq = "2x/week"
        weekly_reason = "Deep hydration support."
    elif primary == "aging":
        weekly = _pick_by_name("All-in-One Gentle Herbal Peel Mask")
        weekly_reason = "Renewal + anti-aging support."
    else:
        weekly = _pick_by_name("Kasturi Manjal Powder")
        weekly_reason = "Maintenance + glow keep panna help pannum."
    
    weekly_name = (weekly.get("name") or "Weekly Care").strip()
    weekly_text = f"Weekly: {weekly_name} ({weekly_freq}) — {weekly_reason}"
    data["weekly_addon"] = weekly_text
    # Routine lines (simple)
    routine = data.get("routine") or {}
    routine.setdefault("morning", f"Morning: Cleanse = {soap.get('name')}  →  Tone = {toner.get('name')}")
    routine.setdefault("night", f"Night: Cleanse = {soap.get('name')}  →  HERO = {hero.get('name')}")
    routine.setdefault("optional", f"Optional: Gel = {gel.get('name')}")
    data["routine"] = routine
    # ---------- Fonts ----------
    try:
        pdfmetrics.registerFont(TTFont("DejaVu", "DejaVuSans.ttf"))
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", "DejaVuSans-Bold.ttf"))
        FONT = "DejaVu"
        FONT_B = "DejaVu-Bold"
    except Exception:
        FONT = "Helvetica"
        FONT_B = "Helvetica-Bold"
    # ---------- Canvas ----------
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    margin_x = 36
    top_y = H - 40
    y = top_y
    subtle = colors.HexColor("#6B7280")
    line_grey = colors.HexColor("#E5E7EB")
    accent = colors.HexColor("#2563EB")
    client_bg  = colors.HexColor("#ECFDF5")
    assess_bg  = colors.HexColor("#EFF6FF")
    routine_bg = colors.HexColor("#F0F9FF")
    weekly_bg  = colors.HexColor("#FFF7ED")
    support_bg = colors.HexColor("#F5F3FF")
    reason_bg  = colors.HexColor("#F3F4F6")
    hero_bg = colors.HexColor("#FEF3C7")
    hero_bd = colors.HexColor("#F59E0B")
    def new_page():
        nonlocal y
        c.showPage()
        y = top_y
    def ensure(space: float):
        nonlocal y
        if y - space < 40:
            new_page()
    def txt(x, y_, s, font=FONT, size=12, color=colors.black):
        c.setFont(font, size)
        c.setFillColor(color)
        c.drawString(x, y_, str(s))
    def rtxt(x, y_, s, font=FONT, size=12, color=colors.black):
        c.setFont(font, size)
        c.setFillColor(color)
        c.drawRightString(x, y_, str(s))
    def hr(y_, color=line_grey, thickness=1):
        c.setStrokeColor(color)
        c.setLineWidth(thickness)
        c.line(margin_x, y_, W - margin_x, y_)
    def section_header(label: str, bg=reason_bg, fg=colors.black):
        nonlocal y
        ensure(56)
        y -= 10
        c.setFillColor(bg)
        c.setStrokeColor(bg)
        c.roundRect(margin_x, y - 24, W - 2 * margin_x, 28, 6, fill=1, stroke=0)
        txt(margin_x + 12, y - 18, label, font=FONT_B, size=13, color=fg)
        y -= 46
    def kv(key: str, value: str, key_w: float = 120):
        nonlocal y
        ensure(22)
        txt(margin_x, y, key, font=FONT_B, size=11, color=subtle)
        txt(margin_x + key_w, y, value if value else "—", font=FONT, size=12, color=colors.black)
        y -= 18
    def wrap_text(value: str, max_w: float, font=FONT, size=11):
        words = (value or "").split()
        lines = []
        cur = ""
        for w_ in words:
            t = (cur + " " + w_).strip()
            if c.stringWidth(t, font, size) <= max_w:
                cur = t
            else:
                if cur:
                    lines.append(cur)
                cur = w_
        if cur:
            lines.append(cur)
        return lines
    def draw_image(img: Image.Image, x: float, y_top: float, w: float, h: float):
        if img is None:
            return
        try:
            ir = ImageReader(img)
        except Exception:
            return
        iw, ih = img.size
        if iw <= 0 or ih <= 0:
            return
        scale = min(w / iw, h / ih)
        dw, dh = iw * scale, ih * scale
        c.drawImage(ir, x + (w - dw) / 2, (y_top - h) + (h - dh) / 2, dw, dh, mask="auto")
    # ---------- Header (fixed overlap) ----------
    txt(margin_x, y, f"{brand_name} — Herbal Skin Coach Report", font=FONT_B, size=18)
    y -= 18
    txt(margin_x, y, f"Instagram: {instagram}", font=FONT, size=11, color=subtle)
    rtxt(W - margin_x, y, ts_str, font=FONT, size=11, color=subtle)
    y -= 10
    hr(y)
    y -= 18
    # ---------- Client Details ----------
    section_header("Client Details", bg=client_bg, fg=colors.HexColor("#065F46"))
    client = data.get("client", {}) or {}
    kv("Client", client.get("name", "—"))
    kv("Phone", client.get("phone", "—"))
    kv("Ref ID", client.get("ref_id", "—"))
    kv("Session", str(data.get("session_id", "—")))
    kv("Date", ts_str)
    y -= 6
    # ---------- Assessment Summary ----------
    section_header("Assessment Summary", bg=assess_bg, fg=colors.HexColor("#1E3A8A"))
    kv("Skin Type", skin_type or "—")
    kv("Concerns", ", ".join(concerns) if concerns else "—")
    conf = data.get("confidence", "—")
    if isinstance(conf, (int, float)):
        conf = f"{int(round(conf * 100))}%"
    kv("Confidence", str(conf))
    y -= 10
    # ---------- HERO box ----------
    ensure(170)
    box_h = 148  # slightly taller to fit consistency note
    c.setFillColor(hero_bg)
    c.setStrokeColor(hero_bd)
    c.setLineWidth(1.5)
    c.roundRect(margin_x, y - box_h + 12, W - 2 * margin_x, box_h, 10, fill=1, stroke=1)
    txt(margin_x + 12, y - 6, "Main Recommendation (HERO) — Ungaluku best pick", font=FONT_B, size=13, color=colors.HexColor("#92400E"))
    txt(margin_x + 12, y - 30, hero.get("name"), font=FONT_B, size=18, color=colors.black)
    inner_w = W - 2 * margin_x - 24
    yy = y - 52
    for label, val in [
        ("Type", hero.get("type", "")),
        ("Why", hero.get("why", "")),
        ("Usage", hero.get("usage", "")),
        ("Note", hero.get("restrictions", "")),
    ]:
        if not val:
            continue
        txt(margin_x + 12, yy, f"{label}:", font=FONT_B, size=11, color=subtle)
        lines = wrap_text(str(val), inner_w - 90, font=FONT, size=11)
        for ln in lines[:2]:
            txt(margin_x + 88, yy, ln, font=FONT, size=11, color=colors.black)
            yy -= 14
        yy -= 2
    # ✅ 21-day consistency note (LOCKED ADD)
    consistency_note = (
        "21 days consistent-a follow pannina visible improvement expect pannalam. "
        "Results person-to-person vary aagalam."
    )
    # keep within hero box (don’t overflow)
    if yy > (y - box_h + 34):
        for ln in wrap_text(consistency_note, inner_w, font=FONT, size=10)[:2]:
            txt(margin_x + 12, yy, ln, font=FONT, size=10, color=subtle)
            yy -= 12
    y = y - box_h - 18
    y -= 10
    # ---------- Routine ----------
    section_header("Routine (Simple) — Easy ah follow pannunga", bg=routine_bg, fg=colors.HexColor("#0C4A6E"))
    kv("Morning", routine.get("morning", "—"))
    kv("Night", routine.get("night", "—"))
    kv("Optional", routine.get("optional", "—"))
    y -= 10
    # ---------- Weekly Add-on ----------
    section_header("Weekly Add-On — Strong Support", bg=weekly_bg, fg=colors.HexColor("#7C2D12"))
    ensure(44)
    txt(margin_x + 6, y, u"•", font=FONT_B, size=12, color=accent)
    for ln in wrap_text(weekly_text, W - 2*margin_x - 20, font=FONT, size=11):
        txt(margin_x + 18, y, ln, font=FONT, size=11, color=colors.black)
        y -= 14
    y -= 6
    # ---------- Result Expectation & Follow-Up Guidance (LOCKED ADD) ----------
    # NOTE: Informational only; does NOT change scoring / product selection.
    section_header(
        "Result Expectation & Follow-Up Guidance",
        bg=colors.HexColor("#EEF2FF"),
        fg=colors.HexColor("#1E3A8A"),
    )
    ensure(84)
    _ginfo = dynamic_report_guidance(
        goal=str(data.get("goal", "")),
        skin_type=str(data.get("skin_type", "")),
        concerns=data.get("concerns", []) if isinstance(data.get("concerns", []), list) else [],
    )
    # Combine expectation + top guidelines (keep short for PDF)
    expect_lines = list(_ginfo.get("expectation", []))[:4] + list(_ginfo.get("guidelines", []))[:3]
    for line in expect_lines:
        ensure(18)
        txt(margin_x, y, u"•", font=FONT_B, size=12, color=accent)
        for ln in wrap_text(line, W - 2 * margin_x - 18, font=FONT, size=11):
            txt(margin_x + 14, y, ln, font=FONT, size=11, color=colors.HexColor("#111827"))
            y -= 14
        y -= 4
    y -= 10
    # ---------- Gentle ethical guidance line (LOCKED ADD) ----------
    ensure(28)
    guidance_big = "We recommend what your skin needs, not what we want to sell."
    guidance_small = "If this suits you, our team can guide you further."
    strong_note = colors.HexColor("#111827")   # darker
    sub_note    = colors.HexColor("#4B5563")   # medium grey
    # Premium callout (cream + gold border) to highlight ethical statement
    callout_h = 36
    callout_w = W - 2 * margin_x
    c_x = margin_x
    c_y = y + 10  # top reference
    # Use the active reportlab canvas `c` (avoid NameError)
    c.setStrokeColor(colors.HexColor("#D4AF37"))
    c.setFillColor(colors.HexColor("#F7F3E9"))
    try:
        c.roundRect(c_x, c_y - callout_h, callout_w, callout_h, 10, stroke=1, fill=1)
    except Exception:
        c.rect(c_x, c_y - callout_h, callout_w, callout_h, stroke=1, fill=1)
    # Text inside
    txt(c_x + 12, c_y - 14, guidance_big, font=FONT_B, size=12, color=colors.HexColor("#1F5D3B"))
    txt(c_x + 12, c_y - 28, guidance_small, font=FONT, size=10, color=sub_note)
    y = c_y - callout_h - 16
    
    # ---------- Bundle Suggestion (Soft / Professional) ----------
    def _safe_name(p: Any, fallback: str) -> str:
        try:
            if isinstance(p, dict):
                return (p.get("name") or fallback).strip()
            if isinstance(p, str):
                return p.strip() or fallback
        except Exception:
            pass
        return fallback
    bundle_items = [
        _safe_name(hero, "HERO Product"),
        _safe_name(soap, "Cleanser"),
        _safe_name(toner, "Toner"),
        _safe_name(gel, "Gel"),
        _safe_name(weekly, "Weekly Add-on"),
    ]
    seen = set()
    bundle_items = [x for x in bundle_items if x and not (x in seen or seen.add(x))]
    bundle_title = "Complete Routine Kit (Optional)"
    bundle_line_1 = "This routine works best when followed as a complete system."
    bundle_line_2 = "Includes: " + " + ".join(bundle_items)
    bundle_line_3 = "If needed, our team can guide you with the complete kit."
    ensure(110)
    bundle_bg = colors.HexColor("#EEF2FF")   # light indigo tint
    bundle_bd = colors.HexColor("#C7D2FE")   # indigo border
    bundle_title_col = colors.HexColor("#111827")
    bundle_text_col = colors.HexColor("#374151")
    bundle_sub_col = colors.HexColor("#6B7280")
    bundle_w = (W - 2 * margin_x) - 60
    bundle_x = margin_x + 30
    bundle_h = 86
    c.setFillColor(bundle_bg)
    c.setStrokeColor(bundle_bd)
    c.setLineWidth(1)
    c.roundRect(bundle_x, y - bundle_h + 10, bundle_w, bundle_h, 10, fill=1, stroke=1)
    txt(bundle_x + 14, y - 10, bundle_title, font=FONT_B, size=12, color=bundle_title_col)
    ty = y - 28
    for ln in wrap_text(bundle_line_1, bundle_w - 28, font=FONT, size=10):
        txt(bundle_x + 14, ty, ln, font=FONT, size=10, color=bundle_text_col)
        ty -= 12
    for ln in wrap_text(bundle_line_2, bundle_w - 28, font=FONT_B, size=10):
        txt(bundle_x + 14, ty, ln, font=FONT_B, size=10, color=bundle_text_col)
        ty -= 12
    for ln in wrap_text(bundle_line_3, bundle_w - 28, font=FONT, size=9):
        txt(bundle_x + 14, ty, ln, font=FONT, size=9, color=bundle_sub_col)
        ty -= 11
    y = y - bundle_h - 16
    # ---------- Supporting Picks (dynamic reasons + better readability) ----------
    section_header("Supporting Picks — Why (Soap/Toner/Gel)", bg=support_bg, fg=colors.HexColor("#4C1D95"))
    def _support_reason(kind: str) -> str:
        st = (skin_type_l or "").lower()
        pr = (primary or "maintenance").lower()
        if kind == "soap":
            if pr == "acne":
                return "Reason: Deep cleanse + acne-support; excess oil/impurities remove pannum."
            if pr == "pigment":
                return "Reason: Gentle cleanse; dullness/tan build-up reduce panna help."
            if "oily" in st:
                return "Reason: Oil control + clean feel; pores clog aagama help."
            if "dry" in st:
                return "Reason: Mild cleanse; skin dry aagama protect pannum."
            return "Reason: Gentle cleanse; daily use-ku safe."
        if kind == "toner":
            if pr == "acne":
                return "Reason: Fresh feel + calming; irritation/redness reduce panna help."
            if pr == "pigment":
                return "Reason: Skin soothe + glow support; dull look reduce panna help."
            if "dry" in st:
                return "Reason: Hydration support + softness; tightness reduce pannum."
            return "Reason: pH balance + fresh feel; routine stable-aa maintain pannum."
        # gel
        if pr == "aging":
            return "Reason: Firmness + antioxidant support; skin look healthy-aa maintain pannum."
        if pr == "pigment":
            return "Reason: Brightening support; uneven tone dullness reduce panna help."
        if pr == "acne":
            return "Reason: Soothing + light hydration; irritation calm pannum."
        if "dry" in st:
            return "Reason: Deep hydration; dryness/roughness reduce panna help."
        return "Reason: Hydration + soothing; redness/irritation reduce panna help."
    def support_line(title: str, reason: str):
        nonlocal y
        ensure(62)
        txt(margin_x, y, title, font=FONT_B, size=12, color=colors.black)
        y -= 16
        reason_color = colors.HexColor("#111827")
        for ln in wrap_text(reason, W - 2 * margin_x, font=FONT, size=11):
            txt(margin_x, y, ln, font=FONT, size=11, color=reason_color)
            y -= 14
        y -= 10
    support_line(f"✅ Soap — {_safe_name(soap, 'Soap')}",  _support_reason("soap"))
    support_line(f"✅ Toner — {_safe_name(toner, 'Toner')}", _support_reason("toner"))
    support_line(f"✅ Gel — {_safe_name(gel, 'Gel')}",   _support_reason("gel"))
    # ---------- Key Reasons ----------
    section_header("Why this Result (Key Reasons)", bg=reason_bg, fg=colors.HexColor("#111827"))
    reasons = data.get("reasons", []) or []
    if not reasons:
        reasons = ["Photos + skin signals based estimate. Result stable-aa irukka try pannirukom."]
    for r in reasons[:5]:
        ensure(18)
        txt(margin_x, y, u"•", font=FONT_B, size=12, color=accent)
        for ln in wrap_text(str(r), W - 2*margin_x - 18, font=FONT, size=11):
            txt(margin_x + 14, y, ln, font=FONT, size=11, color=colors.black)
            y -= 14
        y -= 4
    y -= 10
    # ---------- How this works (ST markdown summary) (LOCKED ADD) ----------
    # Short, print-friendly summary (no external links).
    section_header("How this works (Summary)", bg=colors.HexColor("#F8FAFC"), fg=colors.HexColor("#0F172A"))
    ensure(72)
    st_lines = [
        "Photo-based estimate using visible skin signals (AI-assisted).",
        "Not a medical diagnosis; for severe issues consult a dermatologist.",
        "Best results: consistent routine + sunscreen (day) + hydration.",
        "If results are slow after 21 days, we can review steps & adjust routine.",
    ]
    for line in st_lines:
        ensure(16)
        txt(margin_x, y, u"•", font=FONT_B, size=12, color=accent)
        for ln in wrap_text(line, W - 2 * margin_x - 18, font=FONT, size=10):
            txt(margin_x + 14, y, ln, font=FONT, size=10, color=colors.HexColor("#111827"))
            y -= 12
        y -= 3
    y -= 6
    # ---------- Before/After ----------
    section_header("Before / After Preview (Illustrative)", bg=reason_bg, fg=colors.HexColor("#111827"))
    note = "Idhu motivation-ku dhaan (illustrative). Real results vary by consistency + lifestyle."
    for ln in wrap_text(note, W - 2*margin_x, font=FONT, size=10):
        mid = colors.HexColor("#4B5563")
        txt(margin_x, y, ln, font=FONT, size=10, color=mid)
        y -= 12
    y -= 6
    ensure(220)
    img_h = 170
    img_w = (W - 2 * margin_x - 18) / 2
    top = y
    c.setStrokeColor(colors.HexColor("#D1D5DB"))
    c.setLineWidth(1)
    c.roundRect(margin_x, top - img_h, img_w, img_h, 10, fill=0, stroke=1)
    c.roundRect(margin_x + img_w + 18, top - img_h, img_w, img_h, 10, fill=0, stroke=1)
    txt(margin_x + 8, top + 6, "Before", font=FONT_B, size=11, color=subtle)
    txt(margin_x + img_w + 26, top + 6, "After (preview)", font=FONT_B, size=11, color=subtle)
    draw_image(face_before, margin_x, top, img_w, img_h)
    draw_image(face_after, margin_x + img_w + 18, top, img_w, img_h)
    y = top - img_h - 18
    # ---------- Footer (LOCKED UPDATE) ----------
    hr(44, color=line_grey)
    txt(
        margin_x,
        30,
        "AI-assisted cosmetic guidance. Not a medical diagnosis. Follow routine consistently for best results.",
        font=FONT,
        size=9,
        color=subtle,
    )
    rtxt(W - margin_x, 30, f"{brand_name} • {instagram}", font=FONT, size=9, color=subtle)
    c.save()
    return buf.getvalue()
def reset_for_new_customer():
    keys_to_clear = [
        "analysis",
        "front_img", "left_img", "right_img",
        "front_raw", "left_raw", "right_raw",
        "client_name", "client_phone", "client_ref", "client_notes", "client_consent",
        "page",
        "session_id",
        "force_analyze",
    ]
    for k in keys_to_clear:
        if k in st.session_state:
            del st.session_state[k]
    st.session_state.page = "Upload"
    st.session_state.session_id = str(uuid.uuid4())
    safe_rerun()
# =========================
# SESSION STATE INIT
# =========================
if "page" not in st.session_state:
    st.session_state.page = "Upload"
if "analysis" not in st.session_state:
    st.session_state.analysis = None
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
for k in ["front_img", "left_img", "right_img", "front_raw", "left_raw", "right_raw"]:
    if k not in st.session_state:
        st.session_state[k] = None
for ck in ["client_name", "client_phone", "client_ref", "client_notes", "client_consent"]:
    if ck not in st.session_state:
        st.session_state[ck] = "" if ck != "client_consent" else False
if "selfie_mode" not in st.session_state:
    st.session_state.selfie_mode = True
if "auto_face_crop_on" not in st.session_state:
    st.session_state.auto_face_crop_on = True
if "show_crop_preview" not in st.session_state:
    st.session_state.show_crop_preview = False
# NEW (Option A): show overlay guidance after capture/upload
if "show_guidance_overlay" not in st.session_state:
    st.session_state.show_guidance_overlay = True
# =========================
# HEADER + SIDEBAR
# =========================
st.markdown(
    """
    <div class="ah-hero" style="background:linear-gradient(90deg,var(--ah-cream),#ffffff);border:1px solid rgba(212,175,55,0.35);">
      <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;">
        <div>
          <h2 style="margin:0;color:var(--ah-green);">🍃 Aishwaryam Herbals — Skin Coach</h2>
          <p style="margin:6px 0 0 0;" class="ah-muted">
            Upload → Visible processing (10–15 sec) → Report → PDF/WhatsApp → Follow-ups
          </p>
        </div>
        <div style="display:flex;gap:8px;align-items:center;">
          <span class="ah-badge" style="background:var(--ah-cream);border:1px solid var(--ah-gold);color:var(--ah-green);">✨ 21‑Day Routine</span>
          <span class="ah-badge" style="background:#ffffff;border:1px solid rgba(31,93,59,0.25);color:var(--ah-green);">🌿 Herbal‑first</span>
        </div>
      </div>
    </div>
    """,
    unsafe_allow_html=True
)
with st.sidebar:
    st.markdown(f"## {APP_NAME}")
    st.link_button("Open Instagram", f"https://www.instagram.com/{INSTAGRAM_ID}/")
    st.markdown("---")
    st.session_state.page = st.radio("Navigation", ["Upload", "Report", "History"],
                                     index=["Upload", "Report", "History"].index(st.session_state.page))
    # Quick Actions (always visible on Report page — avoids scrolling)
    if st.session_state.page == "Report":
        st.sidebar.markdown("### ⚡ Quick Actions")
        qa1, qa2 = st.sidebar.columns(2)
        with qa1:
            if st.button("🆕 New", use_container_width=True, key="qa_new_sidebar"):
                reset_for_new_customer()
        with qa2:
            if st.button("🔄 Refresh", use_container_width=True, key="qa_refresh_sidebar"):
                safe_rerun()
        st.sidebar.caption("Tip: Use these buttons anytime (no need to scroll).")
        st.sidebar.markdown("---")
    st.markdown("---")
    st.markdown("---")
    st.session_state.show_guidance_overlay = st.toggle(
        "Show Guidance Overlay (after capture)",
        value=st.session_state.show_guidance_overlay
    )
    
# =========================
# PAGE: UPLOAD
# =========================
if st.session_state.page == "Upload":
    st.markdown("### Upload Photos")
    with st.expander("🧭 Photo Guide (Front / Left / Right) — easy to understand"):
        g1, g2, g3 = st.columns(3)
        with g1:
            st.image(make_pose_guide("Front"), use_container_width=True)
        with g2:
            st.image(make_pose_guide("Left"), use_container_width=True)
        with g3:
            st.image(make_pose_guide("Right"), use_container_width=True)
    st.markdown("### 🤳 Selfie Mode (Recommended)")
    s1, s2, s3 = st.columns([1, 1, 1])
    with s1:
        st.session_state.selfie_mode = st.toggle("Selfie Mode ON", value=st.session_state.selfie_mode)
    with s2:
        st.session_state.auto_face_crop_on = st.toggle("Auto Face Crop", value=st.session_state.auto_face_crop_on)
    with s3:
        st.session_state.show_crop_preview = st.toggle("Show Crop Preview", value=st.session_state.show_crop_preview)
    if st.session_state.selfie_mode:
        st.info(
            "📌 **Selfie Tips (Best Accuracy):**\n"
            "- Face straight, neutral expression 😐\n"
            "- Hair away from forehead & cheeks\n"
            "- No makeup / no filter / no beauty mode\n"
            "- Window light (front light) best\n"
            "- Hold camera steady, tap to focus\n"
            "- Take 3 photos: **Front + Left + Right**"
        )
    st.markdown(
        """
        <div class="ah-card" style="background:#f9fff7;border:1px solid #dfeee2;">
        <b>📸 Photo Tips:</b><br>
        • Natural daylight (window light best)<br>
        • <b>No makeup preferred</b> (foundation/beauty filter avoid pannunga)<br>
        • No filter • Avoid flash • Face ~70% frame
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown("### 🧾 Client Details (Optional, for print/reference)")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.session_state.client_name = st.text_input("Name / Nickname", value=st.session_state.client_name)
    with col2:
        st.session_state.client_phone = st.text_input("Phone (optional)", value=st.session_state.client_phone)
    with col3:
        st.session_state.client_ref = st.text_input("Reference ID (optional)", value=st.session_state.client_ref)
    st.session_state.client_notes = st.text_area("Notes (optional)", value=st.session_state.client_notes, height=70)
    st.session_state.client_consent = st.checkbox("Save locally on this device (consent)",
                                                  value=bool(st.session_state.client_consent))
    st.markdown("---")
    st.markdown("### 📷 Guided Capture (Front → Left → Right)")
    st.caption("One-by-one guided capture for easy mobile use. Complete all 3 angles for best accuracy.")

    def preprocess_image_for_upload(pil_img: Image.Image, max_side: int = 1600) -> Image.Image:
        """Normalize orientation, convert to RGB, and downscale huge images for faster processing."""
        try:
            pil_img = ImageOps.exif_transpose(pil_img)
        except Exception:
            pass
        if pil_img.mode not in ("RGB", "RGBA"):
            pil_img = pil_img.convert("RGB")
        if pil_img.mode == "RGBA":
            bg = Image.new("RGB", pil_img.size, (255, 255, 255))
            bg.paste(pil_img, mask=pil_img.split()[-1])
            pil_img = bg
        w, h = pil_img.size
        scale = max(w, h) / float(max_side)
        if scale > 1:
            pil_img = pil_img.resize((int(w / scale), int(h / scale)))
        return pil_img

    # Wizard state
    if "capture_step" not in st.session_state:
        st.session_state.capture_step = 0  # 0=Front, 1=Left, 2=Right, 3=Done

    steps = [("front", "Front", "Look straight • Face centered • Neutral expression"),
             ("left", "Left", "Turn head LEFT ~30–45° • Keep eyes forward"),
             ("right", "Right", "Turn head RIGHT ~30–45° • Keep eyes forward")]

    step_idx = int(st.session_state.capture_step)
    progress = min(step_idx, 3) / 3.0
    st.progress(progress, text=f"Step {min(step_idx+1, 3)} of 3")

    if step_idx >= 3:
        st.success("✅ All 3 photos captured! Scroll down to Analyze.")
    else:
        pose_key, pose_label, pose_hint = steps[step_idx]

        with st.container(border=True):
            st.markdown(f"#### Step {step_idx+1}: {pose_label}")
            st.info(pose_hint)

            tab_cam, tab_up = st.tabs(["📷 Camera", "🗂 Upload"])
            with tab_cam:
                cap = st.camera_input(f"Capture {pose_label}", key=f"wiz_cam_{pose_key}_{step_idx}")
                if cap is not None:
                    b = cap.getvalue()
                    h = hashlib.md5(b).hexdigest()
                    if st.session_state.get(f"wiz_hash_{pose_key}") != h:
                        st.session_state[f"wiz_hash_{pose_key}"] = h
                        img = preprocess_image_for_upload(Image.open(cap))
                        set_image(pose_key, img)
                        st.session_state.capture_step = step_idx + 1
                        st.rerun()

            with tab_up:
                up = st.file_uploader(f"Upload {pose_label}", type=["jpg", "jpeg", "png"], key=f"wiz_up_{pose_key}_{step_idx}")
                if up is not None:
                    b = up.getvalue()
                    h = hashlib.md5(b).hexdigest()
                    if st.session_state.get(f"wiz_hash_{pose_key}") != h:
                        st.session_state[f"wiz_hash_{pose_key}"] = h
                        img = preprocess_image_for_upload(Image.open(up))
                        # Optional crop (same as before, but simpler in wizard)
                        with st.expander("✂️ Crop / adjust (optional)", expanded=False):
                            enable = st.checkbox("Enable crop", value=False, key=f"wiz_crop_on_{pose_key}_{step_idx}")
                            zoom = st.slider("Zoom", 1.0, 2.0, 1.15, 0.05, key=f"wiz_zoom_{pose_key}_{step_idx}")
                            sx = st.slider("Left ↔ Right", -0.35, 0.35, 0.0, 0.01, key=f"wiz_sx_{pose_key}_{step_idx}")
                            sy = st.slider("Up ↕ Down", -0.35, 0.35, 0.0, 0.01, key=f"wiz_sy_{pose_key}_{step_idx}")
                            if enable:
                                preview = simple_square_crop(img, zoom=zoom, shift_x=sx, shift_y=sy)
                                st.image(preview, caption="Cropped preview", use_container_width=True)
                                img = preview
                            else:
                                st.caption("Crop disabled — original image will be used.")
                        set_image(pose_key, img)
                        st.session_state.capture_step = step_idx + 1
                        st.rerun()

            nav1, nav2, nav3 = st.columns([1, 1, 2])
            with nav1:
                if st.button("⬅ Back", disabled=(step_idx == 0), use_container_width=True, key=f"wiz_back_{step_idx}"):
                    st.session_state.capture_step = max(0, step_idx - 1)
                    st.rerun()
            with nav2:
                if st.button("🔁 Retake this step", use_container_width=True, key=f"wiz_retake_{pose_key}_{step_idx}"):
                    setattr(st.session_state, f"{pose_key}_raw", None)
                    setattr(st.session_state, f"{pose_key}_img", None)
                    st.session_state.pop(f"wiz_hash_{pose_key}", None)
                    st.rerun()
            with nav3:
                st.caption("Tip: Keep face ~70% of frame • Window/front light • Tap-to-focus")

    st.markdown("---")
    st.markdown("### 🗂️ Optional: Upload any missing angles (Gallery / Files)")
    st.caption("If you prefer, you can still upload images directly for any angle below.")

    # Simple fallback upload (kept for flexibility)
    a, b, c = st.columns(3)
    def upload_with_optional_crop(label: str, key_prefix: str, pose_key: str):
        f = st.file_uploader(label, type=["jpg", "jpeg", "png"], key=key_prefix)
        if not f:
            return
        img = preprocess_image_for_upload(Image.open(f))
        with st.expander("✂️ Crop / adjust (optional)", expanded=False):
            enable = st.checkbox("Enable crop", value=False, key=f"{key_prefix}_crop_on")
            zoom = st.slider("Zoom", 1.0, 2.0, 1.15, 0.05, key=f"{key_prefix}_zoom")
            sx = st.slider("Left ↔ Right", -0.35, 0.35, 0.0, 0.01, key=f"{key_prefix}_sx")
            sy = st.slider("Up ↕ Down", -0.35, 0.35, 0.0, 0.01, key=f"{key_prefix}_sy")
            if enable:
                preview = simple_square_crop(img, zoom=zoom, shift_x=sx, shift_y=sy)
                st.image(preview, caption="Cropped preview", use_container_width=True)
                img = preview
            else:
                st.caption("Crop disabled — original image will be used.")
        set_image(pose_key, img)
    with a:
        upload_with_optional_crop("Upload Front", "u_front", "front")
    with b:
        upload_with_optional_crop("Upload Left", "u_left", "left")
    with c:
        upload_with_optional_crop("Upload Right", "u_right", "right")
    # Preview thumbnails: show face-cropped (what engine uses)

    p1, p2, p3 = st.columns(3)
    with p1:
        if st.session_state.front_img is not None:
            st.image(st.session_state.front_img, width=IMG_SMALL, caption="Front (face crop)")
    with p2:
        if st.session_state.left_img is not None:
            st.image(st.session_state.left_img, width=IMG_SMALL, caption="Left (face crop)")
    with p3:
        if st.session_state.right_img is not None:
            st.image(st.session_state.right_img, width=IMG_SMALL, caption="Right (face crop)")
    # NEW (Option A): Guidance overlay preview (uses RAW photo so they see how to align)
    if st.session_state.show_guidance_overlay:
        st.markdown("### ✅ Alignment Preview (How to take next photo)")
        g1, g2, g3 = st.columns(3)
        with g1:
            if st.session_state.front_raw is not None:
                st.image(add_face_frame_overlay(st.session_state.front_raw, "Front"),
                         use_container_width=True,
                         caption="Front guidance overlay (preview only)")
            else:
                st.info("Capture/Upload Front to see overlay preview.")
        with g2:
            if st.session_state.left_raw is not None:
                st.image(add_face_frame_overlay(st.session_state.left_raw, "Left"),
                         use_container_width=True,
                         caption="Left guidance overlay (preview only)")
            else:
                st.info("Capture/Upload Left to see overlay preview.")
        with g3:
            if st.session_state.right_raw is not None:
                st.image(add_face_frame_overlay(st.session_state.right_raw, "Right"),
                         use_container_width=True,
                         caption="Right guidance overlay (preview only)")
            else:
                st.info("Capture/Upload Right to see overlay preview.")
    photos_count = sum([
        st.session_state.front_img is not None,
        st.session_state.left_img is not None,
        st.session_state.right_img is not None
    ])
    can_analyze = photos_count >= 1
    if photos_count > 0:
        issues_all = []
        eligible_count = 0
        for nm, im in [("Front", st.session_state.front_img),
                       ("Left", st.session_state.left_img),
                       ("Right", st.session_state.right_img)]:
            if im is not None:
                eligible, issues = eligibility_check(im)
                if eligible:
                    eligible_count += 1
                else:
                    issues_all.append((nm, issues))
        if eligible_count == 0:
            # Allow an override when user wants to proceed with low-quality photos.
            if not st.session_state.get("force_analyze", False):
                can_analyze = False
                st.error("❌ Photo not eligible for scan. Please re-scan:")
                for nm, issues in issues_all:
                    st.write(f"**{nm} issues:**")
                    for it in issues:
                        st.write("•", it)
                if st.button("Proceed anyway (accuracy may reduce)", use_container_width=True):
                    st.session_state.force_analyze = True
                    can_analyze = True
                    st.warning("Proceeding anyway. Accuracy may reduce — re-take photos for best results.")
            else:
                st.warning("Proceeding with low-quality photos (accuracy may reduce). Re-take photos for best accuracy.")
    st.info(disclaimer_text())
    st.markdown("---")
    if st.button("Analyze My Skin (10–15 sec) →", disabled=not can_analyze, use_container_width=True):
        st.markdown('<div class="ah-overlay">', unsafe_allow_html=True)
        st.markdown("## ⏳ Processing your skin scan…")
        st.caption("Please wait… we are checking multiple cues for better stability.")
        st.markdown("</div>", unsafe_allow_html=True)
        time.sleep(0.25)
        progress_box = st.container()
        status = progress_box.empty()
        bar = progress_box.progress(0)
        steps = [
            ("Queue joining… beta engine ready-aagudhu 🌀", 8),
            ("Face region map build pannitu irukom…", 10),
            ("Oil/shine cues scan pannitu irukom…", 14),
            ("Redness + spot clusters detect pannitu irukom…", 18),
            ("Tone variance (tan/pigment) check pannitu irukom…", 18),
            ("Combination check (T-zone vs cheeks)…", 12),
            ("Multi-photo average + stability check…", 12),
            ("Final recommendation + report formatting…", 8),
        ]
        total_ticks = sum(t for _, t in steps)
        done = 0
        for msg, ticks in steps:
            status.info(msg)
            for _ in range(ticks):
                done += 1
                bar.progress(int(done / total_ticks * 100))
                time.sleep(0.12)  # ~13 sec
        status.success("✅ Scan complete! Preparing report…")
        time.sleep(0.35)
        res = analyze_photos(st.session_state.front_img, st.session_state.left_img, st.session_state.right_img)
        if not res.get("ok"):
            st.error(res.get("error", "Unknown error"))
        else:
            ts = dt.datetime.now().isoformat(timespec="seconds")
            sid = st.session_state.session_id or str(uuid.uuid4())
            st.session_state.session_id = sid
            client_block = {
                "client_name": st.session_state.client_name,
                "client_phone": st.session_state.client_phone,
                "client_ref": st.session_state.client_ref,
                "client_notes": st.session_state.client_notes,
                "client_consent": bool(st.session_state.client_consent),
            }
            st.session_state.analysis = {"ts": ts, "session_id": sid, **client_block, **res}
            save_session_full(st.session_state.analysis)
            add_history({
                "ts": ts,
                "session_id": sid,
                "client_name": client_block["client_name"],
                "client_phone": client_block["client_phone"],
                "client_ref": client_block["client_ref"],
                "photos_used": res.get("photos_used"),
                "skin_type": res.get("skin_type"),
                "main_product": res.get("main_product"),
                "confidence": float(res.get("confidence", 0.0)),
                "concerns": res.get("concerns", []),
            })
            st.success("Report ready ✅")
            st.session_state.page = "Report"
            safe_rerun()
# =========================
# PAGE: REPORT
# =========================
elif st.session_state.page == "Report":
    data = st.session_state.analysis
    if not data or not data.get("ok"):
        st.warning("No report yet. Go to Upload → Analyze or History → Load.")
        st.stop()


    # --- Result preview (so user can confirm correctly) ---
    st.markdown("### 🔎 Result preview")
    c1, c2, c3 = st.columns(3)
    c1.metric("Skin type", str(data.get("skin_type", "—")))
    c2.metric("Main goal", str(data.get("goal", "—")))
    conf = float(data.get("confidence", 0.0))
    c3.metric("Confidence", f"{int(round(conf*100))}%")
    concerns = data.get("concerns") or []
    if concerns:
        st.markdown("**Key concerns detected:** " + " • ".join([str(x) for x in concerns[:6]]))
    st.caption("This is an estimate based on photo quality + lighting. You can fine-tune below.")

    # --- Smart Confirmation (improves accuracy) ---
    if "analysis_confirmed" not in st.session_state:
        st.session_state.analysis_confirmed = False
    if "analysis_verdict" not in st.session_state:
        st.session_state.analysis_verdict = "Yes"

    with st.expander("✅ Quick confirmation (improves accuracy)", expanded=True):
        st.caption("Based on the preview above: **does this match you?** If not, we fine-tune (we recommend what your skin needs).")
        verdict = st.radio(
            "Does the preview match you?",
            options=["Yes", "Not sure", "No"],
            index=["Yes", "Not sure", "No"].index(st.session_state.analysis_verdict),
            horizontal=True,
            key="analysis_verdict_radio",
        )
        st.session_state.analysis_verdict = verdict

        if verdict == "Yes":
            colA, colB = st.columns([1, 1])
            with colA:
                if st.button("✅ Confirm & continue", use_container_width=True):
                    st.session_state.analysis_confirmed = True
            with colB:
                if st.button("Proceed anyway (accuracy may reduce)", use_container_width=True):
                    st.session_state.analysis_confirmed = True

        elif verdict == "Not sure":
            st.markdown("**Quick 3 questions (10 seconds):**")
            oily_by_noon = st.radio("By noon, does your face look shiny/oily?", ["Yes", "No", "Not sure"], horizontal=True)
            tight_after = st.radio("After facewash, does skin feel tight/dry?", ["Yes", "No", "Not sure"], horizontal=True)
            breakouts = st.radio("Do you get frequent pimples/whiteheads?", ["Yes", "No", "Not sure"], horizontal=True)

            concern_pick = st.multiselect(
                "Main concern (optional)",
                ["Dullness", "Tan", "Pigmentation", "Acne", "Blackheads", "Dryness", "Oiliness", "Dark circles", "Sensitive"],
                default=(st.session_state.analysis.get("concerns") or [])[:2],
            )

            colA, colB = st.columns([1, 1])
            with colA:
                if st.button("Update results", use_container_width=True):
                    st.session_state.analysis = refine_analysis_with_user_confirmation(
                        st.session_state.analysis,
                        verdict="Not sure",
                        oily_by_noon=oily_by_noon,
                        tight_after_wash=tight_after,
                        breakouts=breakouts,
                        manual_concerns=concern_pick,
                    )
                    st.session_state.analysis_confirmed = True
                    st.rerun()
            with colB:
                if st.button("Proceed anyway (accuracy may reduce)", use_container_width=True):
                    st.session_state.analysis_confirmed = True

        else:  # No
            st.warning("No problem — we can correct it quickly.")
            manual_type = st.selectbox(
                "Select skin type",
                ["normal", "oily", "dry", "combination"],
                index=["normal", "oily", "dry", "combination"].index((st.session_state.analysis.get("skin_type") or "normal")),
            )
            manual_goal = st.selectbox(
                "Primary goal",
                ["Glow", "Tan removal", "Pigmentation", "Acne control", "Hydration", "Maintenance"],
                index=0,
            )
            manual_concerns = st.multiselect(
                "Concerns",
                ["Dullness", "Tan", "Pigmentation", "Acne", "Blackheads", "Dryness", "Oiliness", "Dark circles", "Sensitive"],
                default=(st.session_state.analysis.get("concerns") or [])[:2],
            )

            colA, colB, colC = st.columns([1, 1, 1])
            with colA:
                if st.button("Use selected", use_container_width=True):
                    st.session_state.analysis = refine_analysis_with_user_confirmation(
                        st.session_state.analysis,
                        verdict="No",
                        manual_skin_type=manual_type,
                        manual_goal=manual_goal,
                        manual_concerns=manual_concerns,
                    )
                    st.session_state.analysis_confirmed = True
                    st.rerun()
            with colB:
                if st.button("Go to Upload (retake)", use_container_width=True):
                    st.session_state.page = "Upload"
                    st.rerun()
            with colC:
                if st.button("Proceed anyway (accuracy may reduce)", use_container_width=True):
                    st.session_state.analysis_confirmed = True

    if not st.session_state.analysis_confirmed:
        st.stop()

    addons = data["addons"]
    face_primary = st.session_state.front_img or st.session_state.left_img or st.session_state.right_img
    st.subheader("🧾 Summary (stable estimate)")
    c1, c2 = st.columns([1, 1.2])
    with c1:
        if face_primary:
            st.image(face_primary, width=IMG_REPORT, caption="Face preview (what engine used)")
    with c2:
        st.write("**Client Name:**", data.get("client_name", "—") or "—")
        st.write("**Phone:**", data.get("client_phone", "—") or "—")
        st.write("**Ref ID:**", data.get("client_ref", "—") or "—")
        st.write("**Session ID:**", data.get("session_id", "—"))
        st.write("**Date:**", data.get("ts", "—"))
        st.write("**Photos used:**", data["photos_used"], "(", ", ".join(data["photo_labels"]), ")")
        st.write("**Skin type (estimate):**", data["skin_type"])
        st.write("**Concerns:**", ", ".join(data["concerns"]))
        st.write("**Confidence:**", f"{int(float(data['confidence'])*100)}%")
        st.success(tanglish_headline(data["main_product"]))
    st.info(disclaimer_text())
    st.markdown("---")
# =========================
# PREMIUM ACTIONS (Download + WhatsApp) — inside Report page
# =========================
    st.markdown("## ✅ Actions")
    info_chips(data)
    st.markdown("---")
    st.markdown("""
    <style>
    .action-card{
      padding: 16px 16px 12px 16px;
      border-radius: 16px;
      border: 1px solid rgba(120,120,120,0.25);
      background: rgba(255,255,255,0.04);
    }
    .action-title{
      font-size: 18px;
      font-weight: 700;
      margin: 0 0 6px 0;
    }
    .action-sub{
      opacity: 0.85;
      margin: 0 0 12px 0;
    }
    .small-muted{
      opacity: 0.75;
      font-size: 12px;
    }
    </style>
    """, unsafe_allow_html=True)
    left, right = st.columns(2, gap="large")
    # ---- LEFT: Download PDF ----
    with left:
        st.markdown('<div class="action-card">', unsafe_allow_html=True)
        st.markdown('<div class="action-title">⬇️ Download PDF Report</div>', unsafe_allow_html=True)
        st.markdown('<div class="action-sub">One-click attractive PDF your customer can keep.</div>', unsafe_allow_html=True)
        if not REPORTLAB_AVAILABLE:
            st.warning("PDF generation needs ReportLab.")
            st.code("pip install reportlab", language="bash")
        else:
            face_before = face_primary
            face_after = simulate_after_realistic(face_primary, goal=data["goal"]) if face_primary else None
            # Advanced toggles (UI only). If OFF, we skip those elements.
            with st.expander("Advanced (optional)", expanded=False):
                include_face_sim = st.checkbox(
                    "Include face simulation in PDF (if image uploaded)",
                    value=True,
                    key="include_face_sim"
                )
                include_hi = st.checkbox(
                    "Include highlight comparison (before vs after)",
                    value=True,
                    key="include_hi"
                )
                st.caption("These only affect the PDF visuals. Your analysis logic remains unchanged.")
            hi = None
            if include_hi and (face_before and face_after):
                hi = highlight_changes(face_before, face_after)
            pdf_bytes = make_report_pdf_bytes_attractive(
                data,
                face_before,
                face_after if include_face_sim else None,
                highlight=hi
            )
            fname_base = (data.get("client_name") or "Client").strip() or "Client"
            ref = (data.get("client_ref") or "").strip()
            filename = f"Herbal_Skin_Coach_Report_{fname_base}_{ref or data['session_id']}.pdf".replace(" ", "_")
            st.download_button(
                "📥 Download Attractive PDF",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                use_container_width=True
            )
            st.caption("Tip: Use client ref to quickly find reports later.")
        st.markdown('</div>', unsafe_allow_html=True)
    # ---- RIGHT: WhatsApp ----
    with right:
        st.markdown('<div class="action-card">', unsafe_allow_html=True)
        st.markdown('<div class="action-title">📤 Share to WhatsApp</div>', unsafe_allow_html=True)
        st.markdown('<div class="action-sub">Send the report summary instantly to your customer.</div>', unsafe_allow_html=True)
        default_phone = "+919843398171"  # CHANGE THIS to your business WhatsApp number
        phone = st.text_input(
            "WhatsApp number (+91 format)",
            value=default_phone,
            key="wa_phone_report"
        )
        wa_msg = build_whatsapp_report_message(data)
        st.text_area("Message Preview", wa_msg, height=140, key="wa_msg_preview")
        if not is_e164(phone):
            st.error("Please enter a valid E.164 number like +9198XXXXXXXX")
            st.link_button("💬 Open WhatsApp Web", "https://web.whatsapp.com/", use_container_width=True)
        else:
            st.link_button(
                "💬 Share Report via WhatsApp",
                whatsapp_link(phone, wa_msg),
                use_container_width=True
            )
        st.markdown('<div class="small-muted">Note: This opens WhatsApp (app/web). If WhatsApp isn’t installed, WhatsApp Web will open.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    if SHOW_SECONDARY_RESET and st.button("🆕 Start New Customer", use_container_width=True):
        reset_for_new_customer()
    # =========================
    # POST-REPORT CONVERSION TOOLS (21-day + Instagram + Follow-up)
    # =========================
    st.markdown("## 📌 Next Steps (21-Day Journey)")
    # Progress tracking (simple + motivating)
    with st.container(border=True):
        st.markdown("### 📊 Progress Tracker (Optional)")
        day = st.select_slider(
            "Select current day",
            options=[1, 7, 14, 21],
            value=1,
            key="progress_day"
        )
        st.progress(day / 21.0, text=f"Day {day} / 21")
        st.caption("Day 1 → Day 7 → Day 14 → Day 21 ✅")
    # Soft Instagram integration (not forced)
    with st.container(border=True):
        st.markdown("### 📲 Routine guidance & results tracking")
        st.markdown(f"Follow **@{INSTAGRAM_ID}** for routine tips and tracking support. (No restrictions)")
        st.link_button("✨ Open Instagram", f"https://www.instagram.com/{INSTAGRAM_ID}/", use_container_width=True)
    # Book follow-up review (WhatsApp prefilled)
    with st.container(border=True):
        st.markdown("### 💬 Book Follow-Up Review")
        biz_phone = st.text_input(
            "Business WhatsApp (+91)",
            value="+919843398171",
            key="biz_wa_phone_followup"
        )
        booking_msg = (
            "Hi, I completed 21 days routine.\n"
            f"Name: {data.get('client_name','')}\n"
            f"Skin type: {data.get('skin_type','')}\n"
            f"Current issue: {data.get('goal','')}\n"
            f"Session: {data.get('session_id','')}\n"
        )
        if is_e164(biz_phone):
            st.link_button(
                "💬 Book Follow-Up Review on WhatsApp",
                whatsapp_link(biz_phone, booking_msg),
                use_container_width=True
            )
        else:
            st.error("Enter valid E.164 number like +9198XXXXXXXX")
    # 21-day reminder (save + WhatsApp draft)
    with st.container(border=True):
        st.markdown("### 🔔 Set 21-Day Follow-Up Reminder")
        r1, r2 = st.columns(2)
        with r1:
            fu_name = st.text_input("Client name", value=(data.get("client_name") or ""), key="fu_name")
        with r2:
            fu_phone = st.text_input("Client phone (E.164)", value=(data.get("client_phone") or ""), key="fu_phone")
        st.caption("“After 21 days consistent usage, re-check pannalam.”")
        reminder_msg = (
            f"Hi {fu_name.strip() or ''}! 😊\n"
            "21 days routine completed? After 21 days consistent usage, re-check pannalam.\n"
            "Reply here to book your follow-up review."
        ).strip()
        b1, b2 = st.columns(2)
        with b1:
            if st.button("🔔 Save Reminder (Local)", use_container_width=True):
                add_followup({
                    "ts": datetime.now().isoformat(timespec="seconds"),
                    "client_name": fu_name.strip(),
                    "client_phone": fu_phone.strip(),
                    "session_id": data.get("session_id"),
                    "note": "21-day follow-up reminder"
                })
                st.success("Saved locally ✅ (data/followups.json)")
        with b2:
            if fu_phone.strip() and is_e164(fu_phone.strip()):
                st.link_button(
                    "💬 Open WhatsApp Reminder Draft",
                    whatsapp_link(fu_phone.strip(), reminder_msg),
                    use_container_width=True
                )
            else:
                st.info("Enter client phone in E.164 format to generate WhatsApp reminder draft.")
    # Soft bundle suggestion (professional, not pushy)
    with st.container(border=True):
        st.markdown("### ✅ Complete Routine Kit Available (Optional)")
        st.info("Complete routine kit is available if you want. This is optional — you can still follow the routine with what you already have.")
    vspace(25)

    # Next action buttons (equal width)
    st.markdown("---")
    st.markdown("## 🔁 What would you like to do next?")
    na1, na2 = st.columns(2, gap="medium")
    with na1:
        if st.button("🆕 Start New Analysis", use_container_width=True):
            reset_for_new_customer()
    with na2:
        if st.button("🔄 Refresh Report", use_container_width=True):
            safe_rerun()
    st.subheader("⭐ ONE Main Recommendation (no confusion da)")
    st.write(one_line_hero(data["main_product"]))
    product_card(data["main_product"], badge="(Main Hero ⭐)")
    st.subheader("✨ Optional Add-ons")
    o1, o2, o3, o4 = st.columns(4)
    with o1:
        st.markdown("**🧼 Soap**"); st.write(addons["soap"])
    with o2:
        st.markdown("**🌹 Toner**"); st.write(addons["toner"])
    with o3:
        st.markdown("**💧 Gel**"); st.write(addons["gel"] if addons["gel"] else "—")
    with o4:
        st.markdown("**🗓️ Weekly**"); st.write(addons["weekly"] if addons["weekly"] else "—")
    def routine_text(main: str, soap: str, toner: str, gel: Optional[str]) -> str:
        lines = []
        lines.append("Morning (simple):")
        lines.append(f"- Cleanse: {soap}")
        lines.append(f"- Toner: {toner} (fresh fresh 😄)")
        if gel == "Aloe Vera Hydrating Gel":
            lines.append("- Aloe Vera Gel: small amount (hydration boost 💧)")
        lines.append("")
        lines.append("Night (simple):")
        lines.append(f"- Cleanse: {soap}")
        lines.append(f"- Toner: {toner}")
        lines.append(f"- Main hero: {main}")
        if gel and gel != "Aloe Vera Hydrating Gel":
            lines.append(f"- Optional gel: {gel} (if you want, compulsory illa)")
        lines.append("")
        lines.append("Mini-tip: First 3 days slow-aa start. Irritation na stop + patch test.")
        return "\n".join(lines)
    st.subheader("🧴 Routine")
    st.code(routine_text(data["main_product"], addons["soap"], addons["toner"], addons["gel"]), language="text")

    vspace(24)

    # Ethical trust line (attractive, brand-matched)
    st.markdown(
        """
        <div style="border:2px solid var(--ah-gold);background:var(--ah-cream);padding:12px 14px;"
        "border-radius:16px;margin-top:8px;">
          <div style="font-weight:800;color:var(--ah-green);font-size:16px;">🤝 We recommend what your skin needs, not what we want to sell.</div>
          <div style="color:#4B5563;font-size:13px;margin-top:4px;">Professional guidance • No pushy selling • Routine-first approach</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    vspace(20)

    # Dynamic Result / Expectation / Guidelines
    dyn = dynamic_report_guidance(
        goal=str(data.get("goal", "")),
        skin_type=str(data.get("skin_type", "")),
        concerns=data.get("concerns", []) if isinstance(data.get("concerns", []), list) else [],
    )
    st.markdown("### ✅ Result • Expectation • Follow Guidelines")
    cR, cE, cG = st.columns(3)
    with cR:
        st.markdown("**✅ Result (What you may notice)**")
        for ln in dyn.get("result", [])[:4]:
            st.write("•", ln)
    with cE:
        st.markdown("**⏳ Expectation (Timeline)**")
        for ln in dyn.get("expectation", [])[:5]:
            st.write("•", ln)
    with cG:
        st.markdown("**🛡️ Follow Guidelines**")
        for ln in dyn.get("guidelines", [])[:5]:
            st.write("•", ln)
    with st.expander("🔍 Why this result?"):
        for r in data["reasons"]:
            st.write("•", r)
    st.subheader("🪞 Before / After (More realistic — illustration only)")
    if face_primary:
        after = simulate_after_realistic(face_primary, goal=data["goal"])
        col1, col2 = st.columns(2)
        with col1:
            st.image(face_primary, width=IMG_BA, caption="Before")
        with col2:
            st.image(after, width=IMG_BA, caption="After (illustration)")
        with st.expander("Show highlighted changes (where difference)"):
            st.image(highlight_changes(face_primary, after), width=IMG_REPORT)
    st.subheader("🎯 Spot Marking (circles) — Face only")
    if face_primary:
        marked, count = detect_spots_and_draw_circles_face_only(face_primary)
        st.image(marked, width=IMG_REPORT, caption=f"Marked spots (estimate): {count}")
    st.markdown("---")
    st.markdown(method_standards_text())
# =========================
# PAGE: HISTORY
# =========================
elif st.session_state.page == "History":
    st.subheader("🗂️ History & Follow-Ups")
    tab_reports, tab_followups = st.tabs(["🧾 Reports History", "🔔 Follow-Ups"])
    with tab_reports:
        st.info(
            "✅ This app stores reports locally in your PC (data/sessions + data/history.json).\n"
            "For LIVE online website, we can move this to a real database (SQLite/PostgreSQL) + login/phone OTP.\n"
            "Now: you can search & reload old sessions from here."
        )
        hist = load_json(HISTORY_FILE, [])
        if not hist:
            st.info("No history yet.")
        else:
            q = st.text_input("Search by Name / Phone / Ref / Session ID", value="")
            ql = q.strip().lower()
            filtered = []
            for h in hist:
                blob = " ".join([
                    str(h.get("client_name", "")),
                    str(h.get("client_phone", "")),
                    str(h.get("client_ref", "")),
                    str(h.get("session_id", "")),
                    str(h.get("skin_type", "")),
                    str(h.get("main_product", "")),
                    str(h.get("ts", "")),
                ]).lower()
                if (not ql) or (ql in blob):
                    filtered.append(h)
            st.caption(f"Showing {min(len(filtered), 60)} of {len(filtered)} record(s).")
            for h in filtered[:60]:
                conf = int(float(h.get("confidence", 0.0)) * 100)
                who = (h.get("client_name") or "").strip()
                ref = (h.get("client_ref") or "").strip()
                sid = h.get("session_id")
                title = f"{(who+' | ' if who else '')}{(ref+' | ' if ref else '')}{h.get('ts')} — {h.get('main_product')} — {conf}%"
                with st.expander(title):
                    st.write("Client:", who or "—")
                    st.write("Phone:", h.get("client_phone", "—") or "—")
                    st.write("Ref ID:", ref or "—")
                    st.write("Session ID:", sid)
                    st.write("Skin type:", h.get("skin_type", "—"))
                    st.write("Concerns:", ", ".join(h.get("concerns", [])) or "—")
                    cols = st.columns(3)
                    with cols[0]:
                        if st.button("📄 Load Report", key=f"load_{sid}"):
                            full = load_session_full(sid)
                            if not full:
                                st.error("Full session file not found. (data/sessions missing?)")
                            else:
                                st.session_state.analysis = full
                                st.session_state.page = "Report"
                                safe_rerun()
                    with cols[1]:
                        if SHOW_SECONDARY_RESET and st.button("🆕 New Customer", key=f"new_{sid}"):
                            reset_for_new_customer()
                    with cols[2]:
                        st.caption("Tip: For live site, we can add cloud DB + user login for re-check later.")
    with tab_followups:
        st.markdown("### 🔔 Follow-Ups Registry")
        st.caption("These are clients saved from the 21‑day reminder step. You can directly open WhatsApp reminder and mark completed.")
        fol = load_json(FOLLOWUPS_FILE, [])
        if not fol:
            st.info("No follow-ups saved yet.")
        else:
            qf = st.text_input("Search follow-ups (Name / Phone / Session ID)", value="", key="fu_search")
            qfl = qf.strip().lower()
            def _match_fu(r: Dict[str, Any]) -> bool:
                blob = " ".join([
                    str(r.get("client_name","")),
                    str(r.get("client_phone","")),
                    str(r.get("session_id","")),
                    str(r.get("note","")),
                    str(r.get("status","")),
                    str(r.get("ts","")),
                ]).lower()
                return (not qfl) or (qfl in blob)
            filtered_fu = [r for r in fol if _match_fu(r)]

            # Quick filters + sorting (CRM-style)
            fcol1, fcol2, fcol3 = st.columns([1.2, 1.0, 1.0])
            with fcol1:
                status_filter = st.selectbox("Filter", ["All", "Pending", "Overdue", "Completed"], index=0, key="fu_filter")
            with fcol2:
                sort_by = st.selectbox("Sort", ["Overdue first", "Newest first", "Oldest first"], index=0, key="fu_sort")
            with fcol3:
                st.caption("Tip: Overdue = 21+ days and not completed.")


            st.caption(f"Showing {min(len(filtered_fu), 80)} of {len(fol)} follow-up(s).")
            # Helper: compute age in days
            def _age_days(ts: str) -> int:
                try:
                    dt = datetime.fromisoformat(ts)
                    return (datetime.now() - dt).days
                except Exception:
                    return -1
            # Apply filter + sorting
            def _status_of(r: Dict[str, Any]) -> str:
                stt = (r.get("status") or "open").strip().lower()
                ts0 = r.get("ts") or ""
                d = _age_days(ts0) if ts0 else -1
                od = (d >= 21 and stt != "done")
                if stt == "done":
                    return "completed"
                if od:
                    return "overdue"
                return "pending"

            if status_filter != "All":
                want = status_filter.lower()
                filtered_fu = [r for r in filtered_fu if _status_of(r) == want]

            if sort_by == "Newest first":
                filtered_fu.sort(key=lambda r: r.get("ts") or "", reverse=True)
            elif sort_by == "Oldest first":
                filtered_fu.sort(key=lambda r: r.get("ts") or "", reverse=False)
            else:  # Overdue first
                # overdue first, then pending, then completed; within each, newest first
                rank = {"overdue": 0, "pending": 1, "completed": 2}
                filtered_fu.sort(key=lambda r: (rank.get(_status_of(r), 9), -( _age_days(r.get("ts") or "") if (r.get("ts") or "") else -1 )))

            for i, r in enumerate(filtered_fu[:80]):

                name = (r.get("client_name") or "—").strip() or "—"
                phone = (r.get("client_phone") or "").strip()
                sid = r.get("session_id") or "—"
                ts = r.get("ts") or ""
                status = (r.get("status") or "open").strip().lower()
                days = _age_days(ts) if ts else -1
                overdue = (days >= 21 and status != "done")
                status_label = "✅ Completed" if status == "done" else ("⏰ Overdue" if overdue else "🕒 Pending")
                with st.container(border=True):
                    top1, top2, top3, top4 = st.columns([2.2, 2.0, 1.3, 1.3])
                    with top1:
                        st.markdown(f"**{name}**  \\n📞 {phone or '—'}")
                    with top2:
                        st.markdown(f"🧾 Session: **{sid}**  \\n🗓️ Saved: {ts or '—'}")
                    with top3:
                        if days >= 0:
                            st.markdown(f"📆 Days: **{days}**")
                        else:
                            st.markdown("📆 Days: —")
                    with top4:
                        # colored badge using HTML
                        if status == "done":
                            st.markdown("<span class='ah-badge' style='background:#dcfce7;color:#166534;border:1px solid rgba(0,0,0,0.08);'>Completed</span>", unsafe_allow_html=True)
                        elif overdue:
                            st.markdown("<span class='ah-badge' style='background:#fee2e2;color:#991b1b;border:1px solid rgba(0,0,0,0.08);'>Overdue</span>", unsafe_allow_html=True)
                        else:
                            st.markdown("<span class='ah-badge' style='background:#fff7ed;color:#9a3412;border:1px solid rgba(0,0,0,0.08);'>Pending</span>", unsafe_allow_html=True)
                    msg = (
                        f"Hi {name}! 😊\n"
                        "21 days routine completed? After 21 days consistent usage, re-check pannalam.\n"
                        "Reply here to book your follow-up review."
                    )
                    a1, a2, a3 = st.columns([1.2, 1.0, 0.8])
                    with a1:
                        if phone and is_e164(phone):
                            st.link_button("💬 Send Reminder", whatsapp_link(phone, msg), use_container_width=True)
                        else:
                            st.button("💬 Send Reminder", use_container_width=True, disabled=True)
                            st.caption("Invalid/missing phone")
                    with a2:
                        if status != "done":
                            if st.button("✅ Mark Completed", key=f"fu_done_{i}_{sid}", use_container_width=True):
                                # update first matching entry (by ts+sid+phone)
                                for j, rr in enumerate(fol):
                                    if rr.get("ts")==r.get("ts") and rr.get("session_id")==r.get("session_id") and rr.get("client_phone")==r.get("client_phone"):
                                        fol[j]["status"] = "done"
                                        fol[j]["done_ts"] = datetime.now().isoformat(timespec="seconds")
                                        break
                                save_json(FOLLOWUPS_FILE, fol)
                                st.success("Marked completed ✅")
                                safe_rerun()
                        else:
                            st.button("✅ Completed", use_container_width=True, disabled=True)
                    with a3:
                        if st.button("🗑️", key=f"fu_del_{i}_{sid}", use_container_width=True):
                            fol = [rr for rr in fol if not (rr.get("ts")==r.get("ts") and rr.get("session_id")==r.get("session_id") and rr.get("client_phone")==r.get("client_phone"))]
                            save_json(FOLLOWUPS_FILE, fol)
                            st.success("Deleted")
                            safe_rerun()
