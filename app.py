import streamlit as st
from datetime import date, timedelta

from stations import REGIONS, CRAYON_COLORS
from jma_scraper import get_daily_temps, get_normal_temps

# モジュールレベルでキャッシュ定義（ボタンクリックをまたいで正しくキャッシュされる）
@st.cache_data(ttl=3600)
def cached_daily(prec_no, block_no, year, month):
    return get_daily_temps(prec_no, block_no, year, month)

@st.cache_data(ttl=3600 * 6)
def cached_normal(prec_no, block_no, month):
    return get_normal_temps(prec_no, block_no, month)
MAX_ENTRIES = 30
N_COLORS = len(CRAYON_COLORS)  # 10

st.set_page_config(page_title="スイカ収穫時期予測", layout="wide")

# ── グローバル CSS ────────────────────────────────────────────
# トグルボタン (tm{i}): マーカー → 色スウォッチdiv → ボタン の順に並ぶ
#   → 2つ先の兄弟のボタンをスウォッチに重ねる (+ div + div button)
# パレットボタン (pm{i}): マーカー → 10色columnsレイアウト の順に並ぶ
#   → 直後の兄弟内のボタンをスウォッチに重ねる (+ div button)
BUTTON_OVERLAY_CSS = """
    position: absolute !important;
    top: -36px !important;
    left: 0 !important;
    right: 0 !important;
    height: 36px !important;
    min-height: 36px !important;
    opacity: 0 !important;
    z-index: 100 !important;
    margin: 0 !important;
    padding: 0 !important;
    cursor: pointer !important;
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
"""

toggle_rules = "\n".join([
    # stElementContainer限定でスコープを絞り、＋ボタン等への誤適用を防ぐ
    f"[data-testid='stElementContainer']:has(#tm{i}) + [data-testid='stElementContainer'] {{ position: relative !important; z-index: 50 !important; width: 100% !important; }}\n"
    f"[data-testid='stElementContainer']:has(#tm{i}) + [data-testid='stElementContainer'] button {{ {BUTTON_OVERLAY_CSS} width: 100% !important; }}"
    for i in range(MAX_ENTRIES)
])
palette_rules = "\n".join([
    # stElementContainer→stLayoutWrapperへの遷移で絞る
    f"[data-testid='stElementContainer']:has(#pm{i}) + div [data-testid='stVerticalBlock'] [data-testid='stElementContainer']:has(button) {{ width: 100% !important; position: relative !important; z-index: 50 !important; }}\n"
    f"[data-testid='stElementContainer']:has(#pm{i}) + div [data-testid='stVerticalBlock'] button {{ {BUTTON_OVERLAY_CSS} width: 100% !important; }}"
    for i in range(MAX_ENTRIES)
])

st.markdown(f"<style>{toggle_rules}\n{palette_rules}</style>", unsafe_allow_html=True)

st.title("🍉 スイカ収穫時期予測")

# ── 観測所選択 ────────────────────────────────────────────────
st.header("観測所の選択")
col1, col2, col3 = st.columns(3)

region_names = list(REGIONS.keys())
with col1:
    region = st.selectbox("地方", region_names)

pref_names = list(REGIONS[region].keys())
with col2:
    pref = st.selectbox("都道府県", pref_names)

stations = REGIONS[region][pref]
with col3:
    station_name = st.selectbox("観測所", [s["name"] for s in stations])

station = next(s for s in stations if s["name"] == station_name)

# ── 有効積算温度 ─────────────────────────────────────────────
st.header("積算温度の設定")
target_gdd = st.number_input(
    "目標積算温度[°C・日]",
    min_value=100, max_value=3000, value=1000, step=50,
)

# ── ヘルパー ─────────────────────────────────────────────────
color_hex_map = {c["name"]: c["hex"] for c in CRAYON_COLORS}
# 白・黄など明るい色は視認性のため暗い代替色を使う
LIGHT_COLORS = {"#F5F5F5", "#F5D000"}  # 白, 黄

def visible_color(hex_col: str) -> str:
    """明るい色の場合、ラベル・ボーダー用に暗い色を返す。"""
    return "#555555" if hex_col in LIGHT_COLORS else hex_col

def get_color(i: int) -> str:
    key = f"poll_color_{i}"
    if key not in st.session_state:
        # デフォルト色：1回目=赤、2回目=橙、3回目=黄、4回目以降=赤
        default_colors = ["赤", "橙", "黄"]
        st.session_state[key] = default_colors[i] if i < len(default_colors) else "赤"
    return st.session_state[key]


def render_toggle(i: int, hex_col: str):
    """色スウォッチ（クリックでパレット開閉）を描画。"""
    border_col = "#444" if hex_col not in LIGHT_COLORS else "#666"
    st.markdown(
        f'<div style="height:36px; background:{hex_col}; border-radius:6px;'
        f'border:2.5px solid {border_col};'
        f'cursor:pointer;" title="クリックして色を変更"></div>',
        unsafe_allow_html=True,
    )
    # マーカー（CSS tm{i} のアンカー）→ ボタンはマーカーの2つ先の兄弟に位置する
    st.markdown(f'<span id="tm{i}"></span>', unsafe_allow_html=True)
    if st.button(" ", key=f"toggle_{i}"):
        st.session_state[f"show_palette_{i}"] = not st.session_state.get(f"show_palette_{i}", False)
        st.rerun()


def render_palette(i: int):
    """10色パレットを描画。選択するとパレットを閉じる。"""
    st.markdown(f'<span id="pm{i}"></span>', unsafe_allow_html=True)
    cols = st.columns(N_COLORS)
    current = get_color(i)
    for j, c in enumerate(CRAYON_COLORS):
        with cols[j]:
            selected = c["name"] == current
            outline = "outline:3px solid #222; outline-offset:2px;" if selected else ""
            border = f'border:2px solid {"#aaa" if c["hex"] in ("#F5F5F5","#F5D000") else "#ccc"};'
            st.markdown(
                f'<div style="height:36px; background:{c["hex"]}; border-radius:5px;'
                f'{border}{outline}" title="{c["name"]}"></div>',
                unsafe_allow_html=True,
            )
            if st.button(" ", key=f"cp_{i}_{j}"):
                st.session_state[f"poll_color_{i}"] = c["name"]
                st.session_state[f"show_palette_{i}"] = False
                st.rerun()


# ── 受粉日入力 ───────────────────────────────────────────────
st.header("受粉日の入力")

if "poll_count" not in st.session_state:
    st.session_state.poll_count = 3

poll_entries = []
for i in range(st.session_state.poll_count):
    current_color = get_color(i)
    hex_col = color_hex_map[current_color]
    show_palette = st.session_state.get(f"show_palette_{i}", False)

    # 受粉日ラベル（選択色のボーダー）― 白・黄は視認性のため暗色を使用
    vis = visible_color(hex_col)
    st.markdown(
        f'<div style="border:3px solid {vis}; border-radius:8px;'
        f'padding:10px 14px 4px; margin:12px 0 4px;">'
        f'<span style="font-weight:bold; font-size:1.05em; color:{vis};">受粉{i + 1}回目</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # 日付入力 ＋ 色スウォッチトグル
    col_date, col_color = st.columns([6, 1])
    with col_date:
        poll_date = st.date_input(
            "日付",
            value=date.today() - timedelta(days=30),
            max_value=date.today(),
            key=f"poll_date_{i}",
            label_visibility="collapsed",
        )
    with col_color:
        render_toggle(i, hex_col)

    # パレット（開いているときだけ表示）
    if show_palette:
        render_palette(i)

    poll_entries.append({"date": poll_date, "color_name": current_color, "color_hex": hex_col})

st.button("＋ 受粉日を追加", key="add_poll",
          on_click=lambda: st.session_state.update(poll_count=st.session_state.poll_count + 1))

st.divider()

# ── 計算 ─────────────────────────────────────────────────────
if st.button("収穫日を計算する", type="primary"):
    today = date.today()
    st.header("計算結果")

    # 注釈を計算結果のすぐ下に表示
    st.markdown(
        '<p style="font-size:0.85em; color:#888; margin-bottom:16px;">'
        '※ 今後気温が平年値どおりに推移した場合の推定です'
        '</p>',
        unsafe_allow_html=True,
    )

    for idx, entry in enumerate(poll_entries):
        poll_date: date = entry["date"]
        hex_color: str = entry["color_hex"]
        color_name: str = entry["color_name"]

        cumulative = 0.0
        harvest_date = None
        current = poll_date
        actual_cache: dict = {}
        normal_cache: dict = {}

        for _ in range(365):
            yr, mo, dy = current.year, current.month, current.day
            if current <= today:
                key = (station["prec_no"], station["block_no"], yr, mo)
                if key not in actual_cache:
                    actual_cache[key] = cached_daily(station["prec_no"], station["block_no"], yr, mo)
                temp = actual_cache[key].get(dy)
            else:
                key = (station["prec_no"], station["block_no"], mo)
                if key not in normal_cache:
                    normal_cache[key] = cached_normal(station["prec_no"], station["block_no"], mo)
                temp = normal_cache[key].get(dy)

            if temp is not None:
                cumulative += temp
                if harvest_date is None and cumulative >= target_gdd:
                    harvest_date = current
                    break

            current += timedelta(days=1)

        days_elapsed = (harvest_date - poll_date).days if harvest_date else None
        bg = "rgba(0,0,0,0.55)" if hex_color == "#1A1A1A" else "#f5f5f5"
        harvest_str = (
            harvest_date.strftime("%Y年%m月%d日") if harvest_date else "未到達（平年値でも目標未達）"
        )
        days_str = f"受粉から {days_elapsed} 日後" if days_elapsed is not None else ""
        vis_color = visible_color(hex_color)
        days_html = f'<br><span style="font-size:0.9em; color:#888;">{days_str}</span>' if days_str else ""

        st.markdown(
            f'<div style="border-left:8px solid {vis_color}; background:{bg};'
            f'padding:14px 20px; margin-bottom:12px; border-radius:6px;">'
            f'<span style="font-weight:bold; font-size:1em; color:{vis_color};">■ 受粉日 {idx+1}（{color_name}）</span>'
            f'<span style="font-size:0.9em; color:#666; margin-left:8px;">受粉日: {poll_date.strftime("%Y年%m月%d日")}</span><br>'
            f'<span style="font-size:1.6em; font-weight:bold; color:{vis_color}; letter-spacing:0.02em;">収穫予定日: {harvest_str}</span>'
            f'{days_html}'
            f'</div>',
            unsafe_allow_html=True,
        )
