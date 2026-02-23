"""
LP Builder - ノーコードLP量産ツール v2
基礎LPをベースに、テキスト・画像・リンクを差し替えてLP量産
"""
from __future__ import annotations

import json
import copy
import base64
import io
import zipfile
import re
import streamlit as st
from streamlit_quill import st_quill
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

/* Quill エディタ調整 */
.stQuill > div { min-height: 80px; }

/* 画像アップロードエリア */
.img-upload-area { border: 2px dashed #ccc; border-radius: 8px; padding: 12px; text-align: center; }
.img-preview { max-width: 200px; border-radius: 6px; margin-top: 8px; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════
# ── 画像管理ユーティリティ ──
# ══════════════════════════════════════════
def image_to_base64(uploaded_file) -> str:
    """アップロードファイルをBase64データURIに変換"""
    bytes_data = uploaded_file.getvalue()
    mime = uploaded_file.type or "image/png"
    b64 = base64.b64encode(bytes_data).decode()
    return f"data:{mime};base64,{b64}"


def image_uploader(label: str, current_url: str, key: str) -> str:
    """画像アップロード or URL入力のUIコンポーネント。返り値は画像URL/Base64"""
    mode = st.radio(
        f"{label} - ソース選択",
        ["URLで指定", "画像をアップロード"],
        horizontal=True,
        key=f"{key}_mode",
        label_visibility="collapsed",
    )

    if mode == "画像をアップロード":
        uploaded = st.file_uploader(
            f"{label}",
            type=["png", "jpg", "jpeg", "gif", "webp", "svg"],
            key=f"{key}_file",
            label_visibility="collapsed",
        )
        if uploaded:
            b64_url = image_to_base64(uploaded)
            # セッションに保持
            st.session_state.setdefault("uploaded_images", {})[key] = {
                "data_uri": b64_url,
                "filename": uploaded.name,
                "bytes": uploaded.getvalue(),
                "mime": uploaded.type,
            }
            return b64_url
        elif key in st.session_state.get("uploaded_images", {}):
            return st.session_state["uploaded_images"][key]["data_uri"]
        elif current_url and not current_url.startswith("data:"):
            return current_url
        return current_url
    else:
        return st.text_input(f"{label} URL", value=current_url if not current_url.startswith("data:") else "", key=f"{key}_url")


# ══════════════════════════════════════════
# ── テキスト装飾ユーティリティ（WYSIWYG） ──
# ══════════════════════════════════════════
# Quill ツールバー設定（WordPress ブロックエディタ風）
QUILL_TOOLBAR = [
    ["bold", "italic", "underline", "strike"],
    [{"color": []}, {"background": []}],
    [{"size": ["small", False, "large", "huge"]}],
    ["link"],
    ["clean"],
]


def rich_text_input(label: str, value: str, key: str, height: int = 80) -> str:
    """WYSIWYG装飾エディタ。HTMLを返す。
    ツールバー: 太字 / 斜体 / 下線 / 打ち消し / 文字色 / 背景色 / サイズ / リンク
    """
    st.caption(label)
    result = st_quill(
        value=value,
        html=True,
        toolbar=QUILL_TOOLBAR,
        key=key,
        placeholder=f"{label}を入力...",
    )
    return result if result is not None else value


# ══════════════════════════════════════════
# ── コア関数 ──
# ══════════════════════════════════════════
def load_config(path: Path) -> dict:
    """JSONファイルから設定を読み込む"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def render_html(config: dict, for_export: bool = False) -> str:
    """Jinja2テンプレートを使ってHTMLをレンダリング"""
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("lp_template.html")
    return template.render(**config, for_export=for_export)


def init_session_state():
    """セッション状態を初期化"""
    if "config" not in st.session_state:
        st.session_state.config = load_config(DEFAULT_CONFIG)
    if "section_order" not in st.session_state:
        st.session_state.section_order = [
            "hero", "comparison_top", "recommend_section",
            "detail_table", "shops", "flow", "summary_table", "footer"
        ]
    if "uploaded_images" not in st.session_state:
        st.session_state.uploaded_images = {}


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


# ══════════════════════════════════════════
# ── セクション編集UI ──
# ══════════════════════════════════════════
def edit_site_settings(config: dict):
    """サイト基本設定"""
    site = config["site"]
    site["title"] = st.text_input("サイトタイトル", value=site["title"], key="site_title")
    site["subtitle"] = st.text_input("サブタイトル", value=site["subtitle"], key="site_subtitle")
    site["logo_text"] = st.text_input("ロゴテキスト", value=site["logo_text"], key="site_logo")
    st.markdown("**ロゴ画像**（テキストの代わりに画像を使う場合）")
    site["logo_url"] = image_uploader("ロゴ画像", site.get("logo_url", ""), "site_logo_img")
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
    """ヒーローセクション - 画像のみ"""
    hero = config["hero"]
    st.markdown("**メインビジュアル画像**")
    hero["bg_image_url"] = image_uploader("FV画像", hero["bg_image_url"], "hero_bg")
    st.caption("FV/MVは画像1枚で完結します。テキストは画像内に含めてください。")


def edit_comparison_top(config: dict):
    """比較表トップ"""
    comp = config["comparison_top"]
    comp["heading"] = st.text_area("見出し", value=comp["heading"], height=60, key="comp_heading")

    for i, shop in enumerate(comp["shops"]):
        st.markdown(f"**── 業者{i+1} ──**")
        shop["name"] = st.text_input("業者名", value=shop["name"], key=f"comp_shop_name_{i}")
        st.markdown("ロゴ画像")
        shop["logo_url"] = image_uploader(f"ロゴ {shop['name']}", shop["logo_url"], f"comp_shop_logo_{i}")
        shop["link"] = st.text_input("リンクURL", value=shop["link"], key=f"comp_shop_link_{i}")
        shop["cta_text"] = st.text_input("CTAテキスト", value=shop["cta_text"], key=f"comp_shop_cta_{i}")
        for j, metric in enumerate(shop["metrics"]):
            mc1, mc2, mc3 = st.columns([2, 2, 1])
            with mc1:
                metric["label"] = st.text_input("項目名", value=metric["label"], key=f"comp_m_label_{i}_{j}")
            with mc2:
                metric["value"] = st.text_input("値", value=metric["value"], key=f"comp_m_val_{i}_{j}")
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
    rec["heading"] = rich_text_input("見出し", rec["heading"], "rec_heading")


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

            # ロゴ画像
            st.markdown("**ロゴ画像**")
            shop["logo_url"] = image_uploader(f"ロゴ {shop['name']}", shop["logo_url"], f"shop_logo_{i}")

            # ── 要素 ON/OFF ──
            st.markdown("---")
            st.markdown("**表示する要素**")

            # 要素のON/OFFをconfigに保持
            shop.setdefault("visibility", {
                "info": True, "features": True, "reviews": True,
                "campaign": True, "cta": True
            })
            vis = shop["visibility"]

            vis_cols = st.columns(5)
            with vis_cols[0]:
                vis["info"] = st.checkbox("基本情報", value=vis.get("info", True), key=f"shop_vis_info_{i}")
            with vis_cols[1]:
                vis["features"] = st.checkbox("特徴", value=vis.get("features", True), key=f"shop_vis_feat_{i}")
            with vis_cols[2]:
                vis["reviews"] = st.checkbox("口コミ", value=vis.get("reviews", True), key=f"shop_vis_rev_{i}")
            with vis_cols[3]:
                vis["campaign"] = st.checkbox("キャンペーン", value=vis.get("campaign", True), key=f"shop_vis_camp_{i}")
            with vis_cols[4]:
                vis["cta"] = st.checkbox("CTA", value=vis.get("cta", True), key=f"shop_vis_cta_{i}")

            # ── 基本情報 ──
            if vis.get("info", True):
                st.markdown("**基本情報**")
                new_info = {}
                info_keys = list(shop["info"].keys())
                for key in info_keys:
                    val = shop["info"][key]
                    ik1, ik2, ik3 = st.columns([3, 5, 1])
                    with ik1:
                        new_key = st.text_input("項目名", value=key, key=f"shop_info_k_{i}_{key}")
                    with ik2:
                        new_val = st.text_input("値", value=val, key=f"shop_info_v_{i}_{key}")
                    with ik3:
                        delete_info = st.button("✕", key=f"shop_info_del_{i}_{key}")
                    if not delete_info:
                        new_info[new_key] = new_val
                shop["info"] = new_info

                if st.button(f"＋ 基本情報を追加", key=f"add_info_{i}"):
                    shop["info"][f"新項目{len(shop['info'])+1}"] = ""
                    st.rerun()

            # ── 特徴 ──
            if vis.get("features", True):
                st.markdown("**特徴・メリット**")
                for fi, feat in enumerate(shop["features"]):
                    feat["title"] = st.text_input(f"特徴{fi+1} タイトル", value=feat["title"], key=f"shop_feat_t_{i}_{fi}")
                    feat["text"] = rich_text_input(f"特徴{fi+1} 本文", feat["text"], f"shop_feat_x_{i}_{fi}")
                    # 特徴に画像スロット
                    feat.setdefault("image_url", "")
                    feat["image_url"] = image_uploader(f"特徴{fi+1}画像", feat["image_url"], f"shop_feat_img_{i}_{fi}")

                f1, f2 = st.columns(2)
                with f1:
                    if st.button(f"＋ 特徴追加", key=f"add_feat_{i}"):
                        shop["features"].append({"title": "新しい特徴", "text": "説明", "image_url": ""})
                        st.rerun()
                with f2:
                    if len(shop["features"]) > 1 and st.button(f"－ 特徴削除", key=f"rm_feat_{i}"):
                        shop["features"].pop()
                        st.rerun()

            # ── 口コミ ──
            if vis.get("reviews", True):
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

            # ── キャンペーン ──
            if vis.get("campaign", True):
                st.markdown("**キャンペーン**")
                shop["campaign"]["text"] = st.text_input("キャンペーン名", value=shop["campaign"]["text"], key=f"shop_camp_t_{i}")
                shop["campaign"]["sub_text"] = st.text_input("サブテキスト", value=shop["campaign"]["sub_text"], key=f"shop_camp_s_{i}")
                st.markdown("キャンペーン画像")
                shop["campaign"]["image_url"] = image_uploader(
                    f"キャンペーン画像", shop["campaign"].get("image_url", ""), f"shop_camp_img_{i}")

            # ── CTA ──
            if vis.get("cta", True):
                st.markdown("**CTA**")
                shop["cta_text"] = st.text_input("CTAテキスト", value=shop["cta_text"], key=f"shop_cta_t_{i}")
                shop["cta_sub"] = st.text_input("CTAサブテキスト", value=shop["cta_sub"], key=f"shop_cta_s_{i}")

            # ── カード内 任意画像 ──
            st.markdown("---")
            st.markdown("**追加画像スロット**（カード内に自由に画像を入れる）")
            shop.setdefault("extra_images", [])
            for ei, eimg in enumerate(shop["extra_images"]):
                ec1, ec2 = st.columns([4, 1])
                with ec1:
                    shop["extra_images"][ei] = image_uploader(
                        f"追加画像{ei+1}", eimg, f"shop_extra_img_{i}_{ei}")
                with ec2:
                    if st.button("✕", key=f"rm_extra_img_{i}_{ei}"):
                        shop["extra_images"].pop(ei)
                        st.rerun()
            if st.button(f"＋ 画像スロット追加", key=f"add_extra_img_{i}"):
                shop["extra_images"].append("")
                st.rerun()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("＋ 業者カードを追加"):
            new_shop = copy.deepcopy(shops[-1]) if shops else {
                "id": "shop_new", "rank": len(shops) + 1, "name": "新規業者",
                "logo_url": "", "catch_copy": "", "sub_catch": "",
                "link": "#", "info": {}, "features": [], "reviews": [],
                "campaign": {"text": "", "sub_text": "", "image_url": ""},
                "cta_text": "相談する", "cta_sub": "",
                "visibility": {"info": True, "features": True, "reviews": True, "campaign": True, "cta": True},
                "extra_images": [],
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
            # アイコン: テキスト or 画像
            step.setdefault("icon_type", "emoji")
            step["icon_type"] = st.selectbox(
                "種類", ["emoji", "画像"],
                index=0 if step.get("icon_type", "emoji") == "emoji" else 1,
                key=f"flow_ico_type_{i}")
        with c2:
            step["title"] = st.text_input("ステップ名", value=step["title"], key=f"flow_title_{i}")
        with c3:
            step["text"] = st.text_input("説明", value=step["text"], key=f"flow_text_{i}")

        if step["icon_type"] == "emoji":
            step["icon"] = st.text_input("アイコン（絵文字）", value=step.get("icon", "📋"), key=f"flow_ico_{i}")
        else:
            step.setdefault("icon_image_url", "")
            step["icon_image_url"] = image_uploader(f"ステップ{i+1}アイコン画像", step.get("icon_image_url", ""), f"flow_ico_img_{i}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("＋ ステップ追加", key="add_step"):
            flow["steps"].append({"title": "新ステップ", "text": "説明", "icon": "📋", "icon_type": "emoji"})
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
            link["name"] = st.text_input("名前", value=link["name"], key=f"ftr_shop_name_{i}")
        with c2:
            link["link"] = st.text_input("URL", value=link["link"], key=f"ftr_shop_link_{i}")

    st.markdown("**コラムリンク**")
    for i, link in enumerate(footer["column_links"]):
        c1, c2 = st.columns(2)
        with c1:
            link["name"] = st.text_input("名前", value=link["name"], key=f"ftr_col_name_{i}")
        with c2:
            link["link"] = st.text_input("URL", value=link["link"], key=f"ftr_col_link_{i}")


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


# ══════════════════════════════════════════
# ── エクスポート（ZIP） ──
# ══════════════════════════════════════════
def create_export_zip(config: dict) -> bytes:
    """HTML + images/ フォルダをZIPで書き出す。
    Base64画像を実ファイルに変換し、HTMLの参照を相対パスに置換。
    """
    export_config = copy.deepcopy(config)
    image_files = {}  # {filename: bytes}
    img_counter = [0]

    def extract_base64_image(data_uri: str, prefix: str = "img") -> str:
        """data:URI → ファイルに切り出してパスを返す"""
        if not data_uri or not data_uri.startswith("data:"):
            return data_uri
        # data:image/png;base64,xxxxx...
        match = re.match(r"data:(image/\w+);base64,(.*)", data_uri, re.DOTALL)
        if not match:
            return data_uri
        mime = match.group(1)
        ext_map = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif",
                    "image/webp": ".webp", "image/svg+xml": ".svg"}
        ext = ext_map.get(mime, ".png")
        img_counter[0] += 1
        filename = f"{prefix}_{img_counter[0]:03d}{ext}"
        raw_bytes = base64.b64decode(match.group(2))
        image_files[filename] = raw_bytes
        return f"images/{filename}"

    # サイトロゴ
    if export_config["site"].get("logo_url"):
        export_config["site"]["logo_url"] = extract_base64_image(
            export_config["site"]["logo_url"], "logo")

    # Hero
    export_config["hero"]["bg_image_url"] = extract_base64_image(
        export_config["hero"]["bg_image_url"], "hero")

    # 比較表ロゴ
    for s in export_config["comparison_top"]["shops"]:
        s["logo_url"] = extract_base64_image(s["logo_url"], "comp_logo")

    # 業者カード
    for s in export_config["shops"]:
        s["logo_url"] = extract_base64_image(s["logo_url"], "shop_logo")
        if s.get("campaign", {}).get("image_url"):
            s["campaign"]["image_url"] = extract_base64_image(
                s["campaign"]["image_url"], "campaign")
        for feat in s.get("features", []):
            if feat.get("image_url"):
                feat["image_url"] = extract_base64_image(feat["image_url"], "feature")
        for ei, eimg in enumerate(s.get("extra_images", [])):
            if eimg:
                s["extra_images"][ei] = extract_base64_image(eimg, "extra")

    # フロー
    for step in export_config["flow"]["steps"]:
        if step.get("icon_image_url"):
            step["icon_image_url"] = extract_base64_image(step["icon_image_url"], "flow_icon")

    # HTML生成
    html_str = render_html(export_config, for_export=True)

    # ZIP作成
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("index.html", html_str)
        for fname, fbytes in image_files.items():
            zf.writestr(f"images/{fname}", fbytes)
    buf.seek(0)
    return buf.getvalue()


# ══════════════════════════════════════════
# ── メインアプリ ──
# ══════════════════════════════════════════
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
        zip_bytes = create_export_zip(config)
        st.download_button("📦 ZIPエクスポート", zip_bytes, file_name="lp_export.zip", mime="application/zip")
    with tb4:
        if st.button("🔄 デフォルトに戻す"):
            st.session_state.config = load_config(DEFAULT_CONFIG)
            st.session_state.uploaded_images = {}
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
                pass

            # 編集UI
            if visibility.get(section_key, True) and section_key in SECTION_EDITORS:
                with st.expander(f"✏️ {label} を編集", expanded=False):
                    SECTION_EDITORS[section_key](config)

    # ── 右: プレビュー ──
    with right_col:
        st.markdown("### 👁️ プレビュー")

        # プレビューサイズ切替
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

        for i, shop in enumerate(render_config.get("shops", [])):
            shop["rank"] = i + 1

        html_output = render_html(render_config)

        # iframe でプレビュー表示（クリック連動付き）
        iframe_width = f"width: {width}px; margin: 0 auto;" if width else "width: 100%;"
        section_label_map = json.dumps(SECTION_LABELS, ensure_ascii=False)
        iframe_html = f"""
        <div style="{iframe_width} border: 1px solid #ddd; border-radius: 8px; overflow: hidden; background: #fff; position: relative;">
            <div id="section-toast" style="display:none; position:absolute; top:8px; left:50%; transform:translateX(-50%); z-index:999;
                background:rgba(0,120,255,0.9); color:#fff; padding:6px 16px; border-radius:6px; font-size:13px; font-weight:600;
                pointer-events:none; transition:opacity 0.3s;">
            </div>
            <iframe id="lp-preview" srcdoc='{html_output.replace("'", "&#39;")}'
                    style="width: 100%; height: calc(100vh - 160px); min-height: 600px; border: none;"
                    sandbox="allow-same-origin allow-scripts">
            </iframe>
        </div>
        <script>
        (function() {{
            var labels = {section_label_map};
            window.addEventListener('message', function(e) {{
                if (e.data && e.data.type === 'section-click') {{
                    var section = e.data.section;
                    var label = labels[section] || section;

                    // トースト表示
                    var toast = document.getElementById('section-toast');
                    toast.textContent = '✏️ ' + label + ' を編集';
                    toast.style.display = 'block';
                    toast.style.opacity = '1';
                    setTimeout(function() {{ toast.style.opacity = '0'; setTimeout(function(){{ toast.style.display = 'none'; }}, 300); }}, 2000);

                    // 親ページ（Streamlit）のexpanderを探してクリック＆スクロール
                    var mainDoc = window.parent.document;
                    var expanders = mainDoc.querySelectorAll('[data-testid="stExpander"]');
                    for (var i = 0; i < expanders.length; i++) {{
                        var summary = expanders[i].querySelector('summary, [data-testid="stExpanderToggleDetails"]');
                        if (summary) {{
                            var text = summary.textContent || summary.innerText || '';
                            if (text.indexOf(label) !== -1) {{
                                // まだ閉じてたら開く
                                var details = expanders[i].querySelector('details');
                                if (details && !details.open) {{
                                    summary.click();
                                }}
                                // スクロール
                                expanders[i].scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                                // ハイライト
                                expanders[i].style.outline = '2px solid #0078ff';
                                expanders[i].style.outlineOffset = '2px';
                                setTimeout(function() {{
                                    expanders[i].style.outline = 'none';
                                }}, 2500);
                                break;
                            }}
                        }}
                    }}
                }}
            }});
        }})();
        </script>
        """
        st.components.v1.html(iframe_html, height=900, scrolling=False)


if __name__ == "__main__":
    main()
