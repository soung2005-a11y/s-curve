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
    .footer-text {
        text-align: center;
        color: #6b7280;
        font-size: 0.9rem;
        padding-top: 1.2rem;
        padding-bottom: 0.5rem;
    }
    .sidebar-source {
        font-size: 0.78rem;
        color: #6b7280;
        line-height: 1.4;
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
    '<div class="dashboard-subtitle">분기·상권유형·업종 필터를 기준으로 매출 현황과 고객 구성을 함께 확인합니다.</div>',
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

    numeric_cols = [
        "기준_년분기_코드",
        "분기매출액",
        "분기거래건수",
        "남성_매출_금액",
        "여성_매출_금액",
        "연령대_10_매출_금액",
        "연령대_20_매출_금액",
        "연령대_30_매출_금액",
        "연령대_40_매출_금액",
        "연령대_50_매출_금액",
        "연령대_60_이상_매출_금액",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

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


@st.cache_data
def convert_df_to_cp949_csv(dataframe: pd.DataFrame) -> bytes:
    return dataframe.to_csv(index=False).encode("cp949", errors="replace")


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

# 다운로드용 CSV 생성
filtered_csv = convert_df_to_cp949_csv(filtered_data)

st.sidebar.markdown("---")
st.sidebar.download_button(
    label="데이터 다운로드(CSV)",
    data=filtered_csv,
    file_name="filtered_data.csv",
    mime="text/csv",
)

# 사이드바 맨 아래 현재 건수 표시
st.sidebar.markdown(f"**필터링된 데이터: {format_int(len(filtered_data))}건**")

# 데이터 출처
st.sidebar.markdown(
    '<div class="sidebar-source">* 데이터출처: 서울 열린데이터광장(http://data.seoul.go.kr/)</div>',
    unsafe_allow_html=True,
)

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
# 고객 분석용 집계 (filtered_data 기준)
# -------------------------------------------------
gender_df = pd.DataFrame(
    {
        "성별": ["남성", "여성"],
        "매출액": [
            filtered_data["남성_매출_금액"].sum(),
            filtered_data["여성_매출_금액"].sum(),
        ],
    }
)

gender_total = gender_df["매출액"].sum()
if gender_total > 0:
    gender_df["비율"] = gender_df["매출액"] / gender_total
else:
    gender_df["비율"] = 0

gender_df["비율라벨"] = gender_df["비율"].map(lambda x: f"{x:.1%}")
gender_df["매출액라벨"] = gender_df["매출액"].map(format_eok)

age_df = pd.DataFrame(
    {
        "연령대": ["10대", "20대", "30대", "40대", "50대", "60대 이상"],
        "매출액": [
            filtered_data["연령대_10_매출_금액"].sum(),
            filtered_data["연령대_20_매출_금액"].sum(),
            filtered_data["연령대_30_매출_금액"].sum(),
            filtered_data["연령대_40_매출_금액"].sum(),
            filtered_data["연령대_50_매출_금액"].sum(),
            filtered_data["연령대_60_이상_매출_금액"].sum(),
        ],
    }
)
age_df["매출액_억원"] = age_df["매출액"] / 100_000_000
age_df["매출라벨"] = age_df["매출액_억원"].map(lambda x: f"{x:,.1f}억")


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
    ", ".join(selected_industries[:3]) +
    (f" 외 {len(selected_industries)-3}개" if len(selected_industries) > 3 else "")
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
# 탭 구성
# -------------------------------------------------
tab1, tab2 = st.tabs(["💰 매출 현황", "👥 고객 분석"])


# -------------------------------------------------
# 탭 1: 매출 현황
# -------------------------------------------------
with tab1:
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

    sales_chart = (
        (bar + text)
        .properties(height=430)
        .configure_axis(
            labelFontSize=12,
            titleFontSize=13,
            grid=True,
        )
        .configure_view(strokeOpacity=0)
    )

    st.altair_chart(sales_chart, use_container_width=True)

    with st.expander("🔍 업종별 분기매출 TOP 10 데이터 보기"):
        display_df = industry_top10[["업종", "분기매출액", "분기매출액_억원"]].copy()
        display_df["분기매출액"] = display_df["분기매출액"].map(lambda x: f"{x:,.0f}")
        display_df["분기매출액_억원"] = display_df["분기매출액_억원"].map(lambda x: f"{x:,.1f}")
        display_df.columns = ["업종", "분기매출액(원)", "분기매출액(억원)"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)


# -------------------------------------------------
# 탭 2: 고객 분석
# -------------------------------------------------
with tab2:
    st.markdown('<div class="section-title">👫 성별 매출 비중</div>', unsafe_allow_html=True)

    donut_col, summary_col = st.columns([2, 1])

    with donut_col:
        donut = (
            alt.Chart(gender_df)
            .mark_arc(innerRadius=70)
            .encode(
                theta=alt.Theta("매출액:Q"),
                color=alt.Color("성별:N", title="성별"),
                tooltip=[
                    alt.Tooltip("성별:N", title="성별"),
                    alt.Tooltip("매출액:Q", title="매출액", format=",.0f"),
                    alt.Tooltip("비율라벨:N", title="비율"),
                ],
            )
            .properties(height=360)
        )

        donut_text = (
            alt.Chart(pd.DataFrame({"text": ["성별\n매출 비중"]}))
            .mark_text(
                fontSize=18,
                fontWeight="bold",
                align="center",
                baseline="middle",
            )
            .encode(text="text:N")
        )

        st.altair_chart(donut + donut_text, use_container_width=True)

    with summary_col:
        st.markdown("#### 📌 요약")
        for _, row in gender_df.iterrows():
            st.metric(
                label=f"{'🧑' if row['성별'] == '남성' else '👩'} {row['성별']}",
                value=row["비율라벨"],
                help=f"매출액 합계: {row['매출액라벨']}",
            )

    st.markdown("---")
    st.markdown('<div class="section-title">🎯 연령대별 매출액</div>', unsafe_allow_html=True)

    age_bar = (
        alt.Chart(age_df)
        .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8)
        .encode(
            x=alt.X(
                "연령대:N",
                sort=["10대", "20대", "30대", "40대", "50대", "60대 이상"],
                title="연령대",
            ),
            y=alt.Y(
                "매출액_억원:Q",
                title="매출액(억원)",
                axis=alt.Axis(format=",.1f"),
            ),
            tooltip=[
                alt.Tooltip("연령대:N", title="연령대"),
                alt.Tooltip("매출액_억원:Q", title="매출액(억원)", format=",.1f"),
            ],
        )
    )

    age_text = (
        alt.Chart(age_df)
        .mark_text(
            dy=-8,
            fontSize=12,
            fontWeight="bold",
        )
        .encode(
            x=alt.X(
                "연령대:N",
                sort=["10대", "20대", "30대", "40대", "50대", "60대 이상"],
            ),
            y=alt.Y("매출액_억원:Q"),
            text=alt.Text("매출라벨:N"),
        )
    )

    age_chart = (
        (age_bar + age_text)
        .properties(height=420)
        .configure_axis(
            labelFontSize=12,
            titleFontSize=13,
            grid=True,
        )
        .configure_view(strokeOpacity=0)
    )

    st.altair_chart(age_chart, use_container_width=True)

    with st.expander("🔍 고객 분석 데이터 보기"):
        gender_view = gender_df.copy()
        gender_view["매출액"] = gender_view["매출액"].map(lambda x: f"{x:,.0f}")
        gender_view["비율"] = gender_view["비율라벨"]
        gender_view = gender_view[["성별", "매출액", "비율"]]
        gender_view.columns = ["성별", "매출액(원)", "비율"]

        age_view = age_df.copy()
        age_view["매출액"] = age_view["매출액"].map(lambda x: f"{x:,.0f}")
        age_view["매출액_억원"] = age_view["매출액_억원"].map(lambda x: f"{x:,.1f}")
        age_view = age_view[["연령대", "매출액", "매출액_억원"]]
        age_view.columns = ["연령대", "매출액(원)", "매출액(억원)"]

        st.markdown("##### 성별 매출 요약")
        st.dataframe(gender_view, use_container_width=True, hide_index=True)

        st.markdown("##### 연령대별 매출 요약")
        st.dataframe(age_view, use_container_width=True, hide_index=True)


# -------------------------------------------------
# 페이지 하단 푸터
# -------------------------------------------------
st.markdown("---")
st.markdown(
    '<div class="footer-text">Made by 이성호, with AI support</div>',
    unsafe_allow_html=True,
)
