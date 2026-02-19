"""
LP Builder - ノーコードLP量産ツール
基礎LPをベースに、テキスト・画像・リンクを差し替えてLP②を量産する
"""
from __future__ import annotations

import json
import copy
import streamlit as st
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

# ── 定数 ──
ROOT = Path(__file__).parent
TEMPLATE_DIR = ROOT / "templates"
DATA_DIR = ROOT / "data"
DEFAULT_CONFIG = DATA_DIR / "default_config.json"

# ── ページ設定 ──
st.set_page_config(
    page_title="LP Builder",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── カスタムCSS ──
st.markdown("""
<style>
/* 左右2分割レイアウト */
[data-testid="stHorizontalBlock"] > div { min-width: 0 !important; }

/* プレビューiframe */
.preview-frame { border: 1px solid #ddd; border-radius: 8px; background: #fff; }

/* セクション操作 */
.block-header { background: #f0f2f6; padding: 8px 12px; border-radius: 6px;
    margin-bottom: 4px; font-weight: 600; cursor: pointer; }

/* サイドバー非表示 */
[data-testid="stSidebar"] { display: none; }

/* expander内のpadding */
.streamlit-expanderContent { padding-top: 8px !important; }

/* セクションブロック */
div[data-testid="stExpander"] { border: 1px solid #e0e0e0; border-radius: 8px; margin-bottom: 8px; }

/* プレビュー列をスティッキーに */
[data-testid="stHorizontalBlock"] > div:nth-child(2) {
    position: sticky;
    top: 0;
    align-self: flex-start;
    max-height: 100vh;
    overflow-y: auto;
}
</style>
""", unsafe_allow_html=True)


# ── ユーティリティ ──
def load_config(path: Path) -> dict:
    """JSONファイルから設定を読み込む"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def render_html(config: dict) -> str:
    """Jinja2テンプレートを使ってHTMLをレンダリング"""
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("lp_template.html")
    return template.render(**config)


def init_session_state():
    """セッション状態を初期化"""
    if "config" not in st.session_state:
        st.session_state.config = load_config(DEFAULT_CONFIG)
    if "section_order" not in st.session_state:
        st.session_state.section_order = [
            "hero", "comparison_top", "recommend_section",
            "detail_table", "shops", "flow", "summary_table", "footer"
        ]


SECTION_LABELS = {
    "hero": "🎨 ヒーロー（メインビジュアル）",
    "comparison_top": "📊 比較表（トップ）",
    "recommend_section": "💡 おすすめメッセージ",
    "detail_table": "📋 詳細比較表",
    "shops": "🏪 業者カード",
    "flow": "🔄 買取フロー",
    "summary_table": "📝 まとめ比較",
    "footer": "📌 フッター",
}


# ── セクション編集UI ──
def edit_site_settings(config: dict):
    """サイト基本設定"""
    site = config["site"]
    site["title"] = st.text_input("サイトタイトル", value=site["title"], key="site_title")
    site["subtitle"] = st.text_input("サブタイトル", value=site["subtitle"], key="site_subtitle")
    site["logo_text"] = st.text_input("ロゴテキスト", value=site["logo_text"], key="site_logo")
    site["ad_label"] = st.text_input("広告表記", value=site["ad_label"], key="site_ad")


def edit_colors(config: dict):
    """カラー設定"""
    colors = config["colors"]
    c1, c2, c3 = st.columns(3)
    with c1:
        colors["main"] = st.color_picker("メインカラー", value=colors["main"], key="c_main")
        colors["sub"] = st.color_picker("サブカラー（CTA）", value=colors["sub"], key="c_sub")
    with c2:
        colors["text"] = st.color_picker("テキスト色", value=colors["text"], key="c_text")
        colors["bg"] = st.color_picker("背景色", value=colors["bg"], key="c_bg")
    with c3:
        colors["accent"] = st.color_picker("アクセント色", value=colors["accent"], key="c_accent")


def edit_hero(config: dict):
    """ヒーローセクション"""
    hero = config["hero"]
    hero["title"] = st.text_area("メインタイトル", value=hero["title"], height=80, key="hero_title")
    hero["catch"] = st.text_input("キャッチコピー", value=hero["catch"], key="hero_catch")
    hero["sub_title"] = st.text_input("サブタイトル", value=hero["sub_title"], key="hero_sub")
    hero["bg_image_url"] = st.text_input("背景画像URL", value=hero["bg_image_url"], key="hero_bg")

    st.markdown("**バッジ（USP）**")
    new_badges = []
    for i, badge in enumerate(hero["badges"]):
        val = st.text_input(f"バッジ {i+1}", value=badge, key=f"hero_badge_{i}")
        new_badges.append(val)
    hero["badges"] = new_badges

    col1, col2 = st.columns(2)
    with col1:
        if st.button("＋ バッジ追加", key="add_badge"):
            hero["badges"].append("新規\nバッジ")
            st.rerun()
    with col2:
        if len(hero["badges"]) > 1 and st.button("－ 最後を削除", key="rm_badge"):
            hero["badges"].pop()
            st.rerun()


def edit_comparison_top(config: dict):
    """比較表トップ"""
    comp = config["comparison_top"]
    comp["heading"] = st.text_area("見出し", value=comp["heading"], height=60, key="comp_heading")

    for i, shop in enumerate(comp["shops"]):
        st.markdown(f"**── 業者{i+1} ──**")
        shop["name"] = st.text_input(f"業者名", value=shop["name"], key=f"comp_shop_name_{i}")
        shop["logo_url"] = st.text_input(f"ロゴURL", value=shop["logo_url"], key=f"comp_shop_logo_{i}")
        shop["link"] = st.text_input(f"リンクURL", value=shop["link"], key=f"comp_shop_link_{i}")
        shop["cta_text"] = st.text_input(f"CTAテキスト", value=shop["cta_text"], key=f"comp_shop_cta_{i}")
        for j, metric in enumerate(shop["metrics"]):
            mc1, mc2, mc3 = st.columns([2, 2, 1])
            with mc1:
                metric["label"] = st.text_input(f"項目名", value=metric["label"], key=f"comp_m_label_{i}_{j}")
            with mc2:
                metric["value"] = st.text_input(f"値", value=metric["value"], key=f"comp_m_val_{i}_{j}")
            with mc3:
                metric["rating"] = st.selectbox(
                    "評価", ["double_circle", "circle", "triangle"],
                    index=["double_circle", "circle", "triangle"].index(metric["rating"]),
                    key=f"comp_m_rate_{i}_{j}",
                    format_func=lambda x: {"double_circle": "◎", "circle": "○", "triangle": "△"}[x]
                )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("＋ 業者追加", key="add_comp_shop"):
            comp["shops"].append({
                "name": "新規業者", "logo_url": "", "link": "#",
                "metrics": [{"label": "項目", "value": "値", "rating": "circle"}],
                "cta_text": "【無料】申込みへ"
            })
            st.rerun()
    with col2:
        if len(comp["shops"]) > 1 and st.button("－ 最後を削除", key="rm_comp_shop"):
            comp["shops"].pop()
            st.rerun()


def edit_recommend(config: dict):
    """おすすめメッセージ"""
    rec = config["recommend_section"]
    rec["heading"] = st.text_area("見出し", value=rec["heading"], height=80, key="rec_heading")


def edit_detail_table(config: dict):
    """詳細比較表"""
    dt = config["detail_table"]
    dt["footer_note"] = st.text_input("注記", value=dt["footer_note"], key="dt_note")

    st.markdown("**カラム名（業者名）**")
    new_cols = []
    for i, col in enumerate(dt["columns"]):
        val = st.text_input(f"カラム {i+1}", value=col, key=f"dt_col_{i}")
        new_cols.append(val)
    dt["columns"] = new_cols

    st.markdown("**行データ**")
    for i, row in enumerate(dt["rows"]):
        with st.expander(f"行: {row['label']}", expanded=False):
            row["label"] = st.text_input("項目名", value=row["label"], key=f"dt_row_label_{i}")
            for j, val in enumerate(row["cells"]):
                row["cells"][j] = st.text_input(
                    f"{dt['columns'][j] if j < len(dt['columns']) else f'列{j+1}'}",
                    value=val, key=f"dt_row_val_{i}_{j}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("＋ 行を追加", key="add_dt_row"):
            dt["rows"].append({"label": "新項目", "cells": [""] * len(dt["columns"])})
            st.rerun()
    with col2:
        if len(dt["rows"]) > 1 and st.button("－ 最後の行を削除", key="rm_dt_row"):
            dt["rows"].pop()
            st.rerun()


def edit_shops(config: dict):
    """業者カード"""
    shops = config["shops"]

    for i, shop in enumerate(shops):
        with st.expander(f"業者 #{shop['rank']} : {shop['name']}", expanded=(i == 0)):
            shop["name"] = st.text_input("業者名", value=shop["name"], key=f"shop_name_{i}")
            shop["rank"] = st.number_input("ランク", value=shop["rank"], min_value=1, key=f"shop_rank_{i}")
            shop["catch_copy"] = st.text_input("キャッチコピー", value=shop["catch_copy"], key=f"shop_catch_{i}")
            shop["sub_catch"] = st.text_area("サブキャッチ", value=shop["sub_catch"], height=60, key=f"shop_sub_{i}")
            shop["link"] = st.text_input("リンクURL", value=shop["link"], key=f"shop_link_{i}")
            shop["logo_url"] = st.text_input("ロゴURL", value=shop["logo_url"], key=f"shop_logo_{i}")

            st.markdown("**基本情報**")
            new_info = {}
            for key, val in shop["info"].items():
                new_val = st.text_input(key, value=val, key=f"shop_info_{i}_{key}")
                new_info[key] = new_val
            shop["info"] = new_info

            st.markdown("**特徴・メリット**")
            for fi, feat in enumerate(shop["features"]):
                feat["title"] = st.text_input(f"特徴{fi+1} タイトル", value=feat["title"], key=f"shop_feat_t_{i}_{fi}")
                feat["text"] = st.text_area(f"特徴{fi+1} 本文", value=feat["text"], height=80, key=f"shop_feat_x_{i}_{fi}")

            f1, f2 = st.columns(2)
            with f1:
                if st.button(f"＋ 特徴追加", key=f"add_feat_{i}"):
                    shop["features"].append({"title": "新しい特徴", "text": "説明"})
                    st.rerun()
            with f2:
                if len(shop["features"]) > 1 and st.button(f"－ 特徴削除", key=f"rm_feat_{i}"):
                    shop["features"].pop()
                    st.rerun()

            st.markdown("**口コミ**")
            new_reviews = []
            for ri, rev in enumerate(shop["reviews"]):
                val = st.text_area(f"口コミ {ri+1}", value=rev, height=60, key=f"shop_rev_{i}_{ri}")
                new_reviews.append(val)
            shop["reviews"] = new_reviews

            r1, r2 = st.columns(2)
            with r1:
                if st.button(f"＋ 口コミ追加", key=f"add_rev_{i}"):
                    shop["reviews"].append("新しい口コミ")
                    st.rerun()
            with r2:
                if len(shop["reviews"]) > 0 and st.button(f"－ 口コミ削除", key=f"rm_rev_{i}"):
                    shop["reviews"].pop()
                    st.rerun()

            st.markdown("**キャンペーン**")
            shop["campaign"]["text"] = st.text_input("キャンペーン名", value=shop["campaign"]["text"], key=f"shop_camp_t_{i}")
            shop["campaign"]["sub_text"] = st.text_input("サブテキスト", value=shop["campaign"]["sub_text"], key=f"shop_camp_s_{i}")
            shop["campaign"]["image_url"] = st.text_input("画像URL", value=shop["campaign"].get("image_url", ""), key=f"shop_camp_img_{i}")

            st.markdown("**CTA**")
            shop["cta_text"] = st.text_input("CTAテキスト", value=shop["cta_text"], key=f"shop_cta_t_{i}")
            shop["cta_sub"] = st.text_input("CTAサブテキスト", value=shop["cta_sub"], key=f"shop_cta_s_{i}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("＋ 業者カードを追加"):
            new_shop = copy.deepcopy(shops[-1]) if shops else {
                "id": "shop_new", "rank": len(shops) + 1, "name": "新規業者",
                "logo_url": "", "catch_copy": "", "sub_catch": "",
                "link": "#", "info": {}, "features": [], "reviews": [],
                "campaign": {"text": "", "sub_text": "", "image_url": ""},
                "cta_text": "相談する", "cta_sub": ""
            }
            new_shop["id"] = f"shop{len(shops) + 1}"
            new_shop["rank"] = len(shops) + 1
            new_shop["name"] = f"新規業者{len(shops) + 1}"
            shops.append(new_shop)
            st.rerun()
    with col2:
        if len(shops) > 1 and st.button("－ 最後の業者を削除"):
            shops.pop()
            st.rerun()


def edit_flow(config: dict):
    """フロー"""
    flow = config["flow"]
    flow["heading"] = st.text_input("見出し", value=flow["heading"], key="flow_heading")

    for i, step in enumerate(flow["steps"]):
        c1, c2, c3 = st.columns([1, 2, 4])
        with c1:
            step["icon"] = st.text_input(f"アイコン", value=step["icon"], key=f"flow_ico_{i}")
        with c2:
            step["title"] = st.text_input(f"ステップ名", value=step["title"], key=f"flow_title_{i}")
        with c3:
            step["text"] = st.text_input(f"説明", value=step["text"], key=f"flow_text_{i}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("＋ ステップ追加", key="add_step"):
            flow["steps"].append({"title": "新ステップ", "text": "説明", "icon": "📋"})
            st.rerun()
    with col2:
        if len(flow["steps"]) > 1 and st.button("－ ステップ削除", key="rm_step"):
            flow["steps"].pop()
            st.rerun()


def edit_summary(config: dict):
    """まとめ比較"""
    st_tbl = config["summary_table"]
    st_tbl["heading"] = st.text_input("見出し", value=st_tbl["heading"], key="sum_heading")

    for i, shop in enumerate(st_tbl["shops"]):
        with st.expander(f"{shop['name']}", expanded=False):
            shop["name"] = st.text_input("業者名", value=shop["name"], key=f"sum_name_{i}")
            shop["features"] = st.text_area("特徴", value=shop["features"], height=60, key=f"sum_feat_{i}")
            shop["scope"] = st.text_area("買取範囲", value=shop["scope"], height=60, key=f"sum_scope_{i}")
            shop["speed"] = st.text_input("スピード", value=shop["speed"], key=f"sum_speed_{i}")
            shop["cta_text"] = st.text_input("CTAテキスト", value=shop["cta_text"], key=f"sum_cta_{i}")
            shop["link"] = st.text_input("リンク", value=shop["link"], key=f"sum_link_{i}")


def edit_footer(config: dict):
    """フッター"""
    footer = config["footer"]
    footer["copyright"] = st.text_input("コピーライト", value=footer["copyright"], key="footer_copy")

    st.markdown("**業者リンク**")
    for i, link in enumerate(footer["shop_links"]):
        c1, c2 = st.columns(2)
        with c1:
            link["name"] = st.text_input(f"名前", value=link["name"], key=f"ftr_shop_name_{i}")
        with c2:
            link["link"] = st.text_input(f"URL", value=link["link"], key=f"ftr_shop_link_{i}")

    st.markdown("**コラムリンク**")
    for i, link in enumerate(footer["column_links"]):
        c1, c2 = st.columns(2)
        with c1:
            link["name"] = st.text_input(f"名前", value=link["name"], key=f"ftr_col_name_{i}")
        with c2:
            link["link"] = st.text_input(f"URL", value=link["link"], key=f"ftr_col_link_{i}")


# セクション → 編集関数のマッピング
SECTION_EDITORS = {
    "hero": edit_hero,
    "comparison_top": edit_comparison_top,
    "recommend_section": edit_recommend,
    "detail_table": edit_detail_table,
    "shops": edit_shops,
    "flow": edit_flow,
    "summary_table": edit_summary,
    "footer": edit_footer,
}


# ── メインアプリ ──
def main():
    init_session_state()
    config = st.session_state.config

    # ── ヘッダー ──
    st.markdown("## 🏗️ LP Builder")
    st.markdown("基礎LPをベースに、テキスト・画像・リンクを差し替えてLP量産")

    # ── ツールバー ──
    tb1, tb2, tb3, tb4, tb5 = st.columns([1, 1, 1, 1, 1])
    with tb1:
        uploaded = st.file_uploader("JSON読込", type=["json"], key="json_upload", label_visibility="collapsed")
        if uploaded:
            try:
                loaded = json.loads(uploaded.read().decode("utf-8"))
                st.session_state.config = loaded
                config = loaded
                st.success("設定を読み込みました")
                st.rerun()
            except Exception as e:
                st.error(f"読み込みエラー: {e}")
    with tb2:
        json_str = json.dumps(config, ensure_ascii=False, indent=2)
        st.download_button("💾 JSON保存", json_str, file_name="lp_config.json", mime="application/json")
    with tb3:
        html_str = render_html(config)
        st.download_button("📄 HTMLエクスポート", html_str, file_name="lp_output.html", mime="text/html")
    with tb4:
        if st.button("🔄 デフォルトに戻す"):
            st.session_state.config = load_config(DEFAULT_CONFIG)
            st.rerun()
    with tb5:
        if st.button("📋 設定を複製"):
            st.session_state.config = copy.deepcopy(config)
            st.toast("現在の設定を複製しました")

    st.divider()

    # ── 左右2分割 ──
    left_col, right_col = st.columns([4, 6], gap="medium")

    # ── 左: 操作パネル ──
    with left_col:
        st.markdown("### ⚙️ 操作パネル")

        # サイト設定 & カラー
        with st.expander("🌐 サイト基本設定", expanded=False):
            edit_site_settings(config)

        with st.expander("🎨 カラー設定", expanded=False):
            edit_colors(config)

        st.markdown("---")
        st.markdown("### 📦 セクションブロック")
        st.caption("各セクションを展開して編集。ON/OFFで表示切替")

        # セクション一覧
        visibility = config["sections_visibility"]
        order = st.session_state.section_order

        for idx, section_key in enumerate(order):
            label = SECTION_LABELS.get(section_key, section_key)

            # 表示/非表示トグル + 並び替え
            hdr1, hdr2, hdr3, hdr4 = st.columns([5, 1, 1, 1])
            with hdr1:
                visibility[section_key] = st.checkbox(
                    label, value=visibility.get(section_key, True),
                    key=f"vis_{section_key}")
            with hdr2:
                if idx > 0 and st.button("↑", key=f"up_{section_key}"):
                    order[idx], order[idx-1] = order[idx-1], order[idx]
                    st.rerun()
            with hdr3:
                if idx < len(order) - 1 and st.button("↓", key=f"dn_{section_key}"):
                    order[idx], order[idx+1] = order[idx+1], order[idx]
                    st.rerun()
            with hdr4:
                pass  # placeholder

            # 編集UI
            if visibility.get(section_key, True) and section_key in SECTION_EDITORS:
                with st.expander(f"✏️ {label} を編集", expanded=False):
                    SECTION_EDITORS[section_key](config)

    # ── 右: プレビュー ──
    with right_col:
        st.markdown("### 👁️ プレビュー")

        # プレビューサイズ切替
        pv1, pv2, pv3 = st.columns(3)
        with pv1:
            preview_mode = st.radio(
                "表示サイズ", ["PC (780px)", "SP (375px)", "フル幅"],
                horizontal=True, key="preview_mode", label_visibility="collapsed")

        if preview_mode == "PC (780px)":
            width = 780
        elif preview_mode == "SP (375px)":
            width = 375
        else:
            width = None

        # セクション順序を反映した設定でレンダリング
        render_config = copy.deepcopy(config)

        # セクション順序に応じて shops のランクを更新
        for i, shop in enumerate(render_config.get("shops", [])):
            shop["rank"] = i + 1

        html_output = render_html(render_config)

        # iframe でプレビュー表示
        iframe_width = f"width: {width}px; margin: 0 auto;" if width else "width: 100%;"
        iframe_html = f"""
        <div style="{iframe_width} border: 1px solid #ddd; border-radius: 8px; overflow: hidden; background: #fff;">
            <iframe srcdoc='{html_output.replace("'", "&#39;")}'
                    style="width: 100%; height: calc(100vh - 160px); min-height: 600px; border: none;"
                    sandbox="allow-same-origin">
            </iframe>
        </div>
        """
        st.components.v1.html(iframe_html, height=900, scrolling=False)


if __name__ == "__main__":
    main()
