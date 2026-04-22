from pathlib import Path

import pandas as pd
import streamlit as st


# -----------------------------
# 기본 설정
# -----------------------------
st.set_page_config(
    page_title="서울시 상권 분석 대시보드",
    page_icon="📊",
    layout="wide",
)

st.title("📊 서울시 상권 분석 대시보드")
st.caption("분기별 상권 데이터를 기준으로 핵심 지표를 한눈에 확인합니다.")


# -----------------------------
# 데이터 로드
# -----------------------------
@st.cache_data
def find_csv_file() -> Path:
    """
    main.py와 같은 폴더에서 CSV 파일을 찾습니다.
    우선순위:
    1) 서울시_상권분석서비스_샘플.csv
    2) 같은 폴더의 첫 번째 csv 파일
    """
    base_dir = Path(__file__).resolve().parent
    preferred_file = base_dir / "서울시_상권분석서비스_샘플.csv"

    if preferred_file.exists():
        return preferred_file

    csv_files = list(base_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError("같은 폴더에서 CSV 파일을 찾을 수 없습니다.")

    return csv_files[0]


@st.cache_data
def load_data() -> pd.DataFrame:
    csv_path = find_csv_file()
    df = pd.read_csv(csv_path, encoding="cp949")

    # 컬럼명 변경
    rename_map = {
        "상권_구분_코드_명": "상권유형",
        "상권_코드": "상권코드",
        "상권_코드_명": "상권이름",
        "서비스_업종_코드_명": "업종",
        "당월_매출_금액": "분기매출액",
        "당월_매출_건수": "분기거래건수",
    }
    df = df.rename(columns=rename_map)

    # 숫자형 처리
    numeric_cols = ["기준_년분기_코드", "분기매출액", "분기거래건수"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


df = load_data()


# -----------------------------
# 포맷 함수
# -----------------------------
def format_eok(value: float) -> str:
    """원을 억원 단위로 변환하여 쉼표 포함 문자열 반환"""
    eok = value / 100_000_000
    return f"{eok:,.1f}억"


def format_man_geon(value: float) -> str:
    """건수를 만 건 단위로 변환하여 쉼표 포함 문자열 반환"""
    man = value / 10_000
    return f"{man:,.1f}만 건"


def format_int(value: int) -> str:
    return f"{value:,}"


# -----------------------------
# 사이드바 필터
# -----------------------------
st.sidebar.header("🧭 필터")

quarter_options = ["전체"]
if "기준_년분기_코드" in df.columns:
    unique_quarters = (
        df["기준_년분기_코드"]
        .dropna()
        .astype(int)
        .sort_values()
        .unique()
        .tolist()
    )
    quarter_options += [str(q) for q in unique_quarters]

selected_quarter = st.sidebar.selectbox(
    "분기 선택",
    options=quarter_options,
    index=0,
    help="기본값은 전체이며, 특정 분기를 선택하면 해당 분기 기준으로 메트릭이 반영됩니다.",
)


# -----------------------------
# 필터 적용
# -----------------------------
filtered_df = df.copy()

if selected_quarter != "전체":
    filtered_df = filtered_df[
        filtered_df["기준_년분기_코드"] == int(selected_quarter)
    ]


# -----------------------------
# KPI 계산
# -----------------------------
total_sales = filtered_df["분기매출액"].sum()
total_txn = filtered_df["분기거래건수"].sum()
market_count = filtered_df["상권이름"].nunique()
industry_count = filtered_df["업종"].nunique()


# -----------------------------
# KPI 영역 (4칸)
# -----------------------------
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="💰 총 분기 매출액",
        value=format_eok(total_sales),
        help="선택한 분기 기준 분기매출액 합계입니다.",
    )

with col2:
    st.metric(
        label="🧾 총 분기 거래건수",
        value=format_man_geon(total_txn),
        help="선택한 분기 기준 분기거래건수 합계입니다.",
    )

with col3:
    st.metric(
        label="🏙️ 분석 상권 수",
        value=format_int(market_count),
        help="상권이름의 고유 개수입니다.",
    )

with col4:
    st.metric(
        label="🛍️ 업종 종류",
        value=format_int(industry_count),
        help="업종의 고유 개수입니다.",
    )


st.markdown("---")

# 참고 정보
left, right = st.columns([2, 1])

with left:
    st.subheader("🔎 현재 적용 필터")
    if selected_quarter == "전체":
        st.write("- 분기: 전체")
    else:
        st.write(f"- 분기: {int(selected_quarter):,}")

with right:
    st.subheader("📁 데이터 파일")
    try:
        st.write(find_csv_file().name)
    except Exception:
        st.write("파일 확인 필요")
