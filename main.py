from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


# -------------------------------------------------
# 페이지 설정
# -------------------------------------------------
st.set_page_config(
    page_title="서울시 상권 분석 대시보드",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 2rem;
    }
    .dashboard-title {
        font-size: 2rem;
        font-weight: 800;
        margin-bottom: 0.15rem;
    }
    .dashboard-subtitle {
        color: #6b7280;
        font-size: 0.98rem;
        margin-bottom: 1.1rem;
    }
    .section-title {
        font-size: 1.15rem;
        font-weight: 700;
        margin-top: 0.4rem;
        margin-bottom: 0.8rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="dashboard-title">📊 서울시 상권 분석 대시보드</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="dashboard-subtitle">분기·상권유형·업종 필터를 기준으로 핵심 지표와 업종별 매출 상위를 확인합니다.</div>',
    unsafe_allow_html=True,
)


# -------------------------------------------------
# 데이터 로드
# -------------------------------------------------
@st.cache_data
def find_csv_file() -> Path:
    """
    main.py와 같은 폴더에서 CSV 파일을 찾습니다.
    우선순위:
    1) 서울시_상권분석서비스_샘플.csv
    2) 같은 폴더 내 첫 번째 csv 파일
    """
    base_dir = Path(__file__).resolve().parent
    preferred = base_dir / "서울시_상권분석서비스_샘플.csv"

    if preferred.exists():
        return preferred

    csv_files = sorted(base_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError("main.py와 같은 폴더에서 CSV 파일을 찾지 못했습니다.")

    return csv_files[0]


@st.cache_data
def load_data() -> pd.DataFrame:
    csv_path = find_csv_file()
    df = pd.read_csv(csv_path, encoding="cp949")

    rename_map = {
        "상권_구분_코드_명": "상권유형",
        "상권_코드": "상권코드",
        "상권_코드_명": "상권이름",
        "서비스_업종_코드_명": "업종",
        "당월_매출_금액": "분기매출액",
        "당월_매출_건수": "분기거래건수",
    }
    df = df.rename(columns=rename_map)

    numeric_cols = ["기준_년분기_코드", "분기매출액", "분기거래건수"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


# -------------------------------------------------
# 포맷 함수
# -------------------------------------------------
def format_eok(value: float) -> str:
    eok = value / 100_000_000
    return f"{eok:,.1f}억"


def format_man_geon(value: float) -> str:
    man = value / 10_000
    return f"{man:,.1f}만 건"


def format_int(value: int) -> str:
    return f"{int(value):,}"


# -------------------------------------------------
# 데이터 준비
# -------------------------------------------------
try:
    df = load_data()
    csv_name = find_csv_file().name
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.stop()


# -------------------------------------------------
# 기본 필터 옵션 준비
# -------------------------------------------------
all_quarters = (
    df["기준_년분기_코드"]
    .dropna()
    .astype(int)
    .sort_values()
    .unique()
    .tolist()
)
quarter_options = ["전체"] + [str(q) for q in all_quarters]

market_type_options = sorted(df["상권유형"].dropna().astype(str).unique().tolist())

top5_industries = (
    df.groupby("업종", as_index=False)["분기매출액"]
    .sum()
    .sort_values("분기매출액", ascending=False)
    .head(5)["업종"]
    .tolist()
)

industry_options = sorted(df["업종"].dropna().astype(str).unique().tolist())


# -------------------------------------------------
# 사이드바 필터
# -------------------------------------------------
st.sidebar.header("데이터 필터")

selected_quarters = st.sidebar.multiselect(
    "필터 1: 분기 선택",
    options=quarter_options,
    default=["전체"],
    help="전체가 선택되면 모든 분기를 포함합니다. 특정 분기를 여러 개 선택할 수도 있습니다.",
)

selected_market_types_default = [
    v for v in ["골목상권", "전통시장"] if v in market_type_options
]
selected_market_types = st.sidebar.multiselect(
    "필터 2: 상권유형",
    options=market_type_options,
    default=selected_market_types_default,
)

selected_industries_default = [
    v for v in top5_industries if v in industry_options
]
selected_industries = st.sidebar.multiselect(
    "필터 3: 업종",
    options=industry_options,
    default=selected_industries_default,
)

st.sidebar.markdown("---")
st.sidebar.markdown("### ℹ️ 데이터 정보")
st.sidebar.write(f"**파일명**: {csv_name}")
st.sidebar.write(f"**전체 행 수**: {format_int(len(df))}개")


# -------------------------------------------------
# 필터 적용 → filtered_data
# -------------------------------------------------
filtered_data = df.copy()

# 1) 분기 필터
if selected_quarters:
    if "전체" not in selected_quarters:
        selected_quarter_ints = [int(q) for q in selected_quarters]
        filtered_data = filtered_data[
            filtered_data["기준_년분기_코드"].isin(selected_quarter_ints)
        ]
else:
    filtered_data = filtered_data.iloc[0:0]

# 2) 상권유형 필터
if selected_market_types:
    filtered_data = filtered_data[
        filtered_data["상권유형"].isin(selected_market_types)
    ]
else:
    filtered_data = filtered_data.iloc[0:0]

# 3) 업종 필터
if selected_industries:
    filtered_data = filtered_data[
        filtered_data["업종"].isin(selected_industries)
    ]
else:
    filtered_data = filtered_data.iloc[0:0]

# 사이드바 맨 아래 현재 건수 표시
st.sidebar.markdown("---")
st.sidebar.markdown(f"**필터링된 데이터: {format_int(len(filtered_data))}건**")

if filtered_data.empty:
    st.warning("선택한 조건에 해당하는 데이터가 없습니다. 사이드바 필터를 조정해 주세요.")
    st.stop()


# -------------------------------------------------
# KPI 계산 (filtered_data 기준)
# -------------------------------------------------
total_sales = filtered_data["분기매출액"].sum()
total_txn = filtered_data["분기거래건수"].sum()
market_count = filtered_data["상권이름"].nunique()
industry_count = filtered_data["업종"].nunique()


# -------------------------------------------------
# 상단 상태 표시
# -------------------------------------------------
if not selected_quarters:
    quarter_filter_text = "선택 없음"
elif "전체" in selected_quarters:
    quarter_filter_text = "전체"
else:
    quarter_filter_text = ", ".join([f"{int(q):,}" for q in selected_quarters])

market_type_filter_text = (
    ", ".join(selected_market_types) if selected_market_types else "선택 없음"
)
industry_filter_text = (
    ", ".join(selected_industries[:3]) + (f" 외 {len(selected_industries)-3}개" if len(selected_industries) > 3 else "")
    if selected_industries else "선택 없음"
)

left_info, right_info = st.columns([3, 1])

with left_info:
    st.info(
        f"📌 분기: **{quarter_filter_text}**  |  "
        f"상권유형: **{market_type_filter_text}**  |  "
        f"업종: **{industry_filter_text}**"
    )

with right_info:
    st.success(f"✅ 분석 대상: **{format_int(len(filtered_data))}건**")


# -------------------------------------------------
# KPI 4칸 (filtered_data 기준)
# -------------------------------------------------
st.markdown('<div class="section-title">✨ 핵심 메트릭</div>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="💰 총 분기 매출액",
        value=format_eok(total_sales),
        help="선택한 필터 조건 기준 분기매출액 합계를 억원 단위로 표시합니다.",
    )

with col2:
    st.metric(
        label="🧾 총 분기 거래건수",
        value=format_man_geon(total_txn),
        help="선택한 필터 조건 기준 분기거래건수 합계를 만 건 단위로 표시합니다.",
    )

with col3:
    st.metric(
        label="🏙️ 분석 상권 수",
        value=format_int(market_count),
        help="선택한 필터 조건 기준 상권이름의 고유 개수입니다.",
    )

with col4:
    st.metric(
        label="🛍️ 업종 종류",
        value=format_int(industry_count),
        help="선택한 필터 조건 기준 업종의 고유 개수입니다.",
    )

st.markdown("---")


# -------------------------------------------------
# 차트 계산 (filtered_data 기준)
# -------------------------------------------------
st.markdown('<div class="section-title">🏆 분기 매출 TOP 10 업종</div>', unsafe_allow_html=True)

industry_top10 = (
    filtered_data.groupby("업종", as_index=False)["분기매출액"]
    .sum()
    .sort_values("분기매출액", ascending=False)
    .head(10)
    .copy()
)

industry_top10["분기매출액_억원"] = industry_top10["분기매출액"] / 100_000_000
industry_top10["매출라벨"] = industry_top10["분기매출액_억원"].map(
    lambda x: f"{x:,.1f}억"
)

bar = (
    alt.Chart(industry_top10)
    .mark_bar(cornerRadius=8)
    .encode(
        x=alt.X(
            "분기매출액_억원:Q",
            title="분기매출액(억원)",
            axis=alt.Axis(format=",.1f"),
        ),
        y=alt.Y(
            "업종:N",
            sort="-x",
            title="업종",
        ),
        tooltip=[
            alt.Tooltip("업종:N", title="업종"),
            alt.Tooltip("분기매출액_억원:Q", title="분기매출액(억원)", format=",.1f"),
        ],
    )
)

text = (
    alt.Chart(industry_top10)
    .mark_text(
        align="left",
        baseline="middle",
        dx=7,
        fontSize=12,
        fontWeight="bold",
    )
    .encode(
        x=alt.X("분기매출액_억원:Q"),
        y=alt.Y("업종:N", sort="-x"),
        text=alt.Text("매출라벨:N"),
    )
)

chart = (
    (bar + text)
    .properties(height=430)
    .configure_axis(
        labelFontSize=12,
        titleFontSize=13,
        grid=True,
    )
    .configure_view(strokeOpacity=0)
)

st.altair_chart(chart, use_container_width=True)


# -------------------------------------------------
# 참고용 표 (filtered_data 기준)
# -------------------------------------------------
with st.expander("🔍 업종별 분기매출 TOP 10 데이터 보기"):
    display_df = industry_top10[["업종", "분기매출액", "분기매출액_억원"]].copy()
    display_df["분기매출액"] = display_df["분기매출액"].map(lambda x: f"{x:,.0f}")
    display_df["분기매출액_억원"] = display_df["분기매출액_억원"].map(lambda x: f"{x:,.1f}")
    display_df.columns = ["업종", "분기매출액(원)", "분기매출액(억원)"]
    st.dataframe(display_df, use_container_width=True, hide_index=True)


# -------------------------------------------------
# 하단 안내
# -------------------------------------------------
st.markdown("---")
st.caption("📎 모든 KPI와 차트는 filtered_data 기준으로 계산됩니다.")
