import streamlit as st
import pandas as pd
import altair as alt
import os
from datetime import datetime

# --- 데이터 로드 및 전처리 ---

# CSV 파일 경로
# 사용자가 업로드한 '서울시 구로구 학교 기본정보.csv' 파일을 사용합니다.
FILE_PATH = "서울시 구로구 학교 기본정보.csv"

@st.cache_data
def load_data(file_path):
    # 파일 존재 여부 확인 로직
    # 로컬 환경이 아닌 경우 (Canvas 환경)에는 파일이 자동으로 로드되므로 파일 경로 확인은 주석 처리
    # if not os.path.exists(file_path):
    #     st.error(f"오류: '{file_path}' 파일을 찾을 수 없습니다.")
    #     return None

    try:
        # Streamlit은 파일이 업로드되었을 경우 해당 파일의 경로를 자동으로 처리합니다.
        # cp949 인코딩으로 파일을 읽습니다.
        df_raw = pd.read_csv(file_path, encoding='cp949')
        df_unique = df_raw.drop_duplicates(subset='표준학교코드').copy()
        df_unique['설립일자'] = pd.to_datetime(df_unique['설립일자'], format='%Y%m%d', errors='coerce')
        df_unique['개교기념일'] = pd.to_datetime(df_unique['개교기념일'], format='%Y%m%d', errors='coerce')
        df_unique = df_unique.dropna(subset=['설립일자'])
        return df_raw, df_unique
    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생: {e}")
        return None, None

df_raw, df_unique = load_data(FILE_PATH)

if df_unique is None:
    st.stop()

# --- 사이드바 (페이지 선택 + 필터) ---

# --- 0. 페이지 선택 라디오 버튼 (맨 위로 이동 및 간소화) ---
page_selection = st.sidebar.radio(
    "페이지 선택 📑", # 레이블에 아이콘 포함하여 제목/레이블 간소화
    ('그래프 분석', '학교 목록'),
    horizontal=True # 가로 배치로 수직 공간 최소화
)
st.sidebar.markdown("---") # 구분선 추가

st.sidebar.header("데이터 필터 🔎")

# 1. 학교 종류 필터
school_types = df_unique['학교종류명'].unique()
selected_types = st.sidebar.multiselect('학교 종류 선택', options=school_types, default=school_types)

# 2. 설립 구분 필터
establishment_types = df_unique['설립구분'].unique()
selected_establishments = st.sidebar.multiselect('설립 구분 선택', options=establishment_types, default=establishment_types)

# --- 3. 성별 구분 필터 (공간 효율화) ---
st.sidebar.markdown("---")
st.sidebar.subheader("성별 구분 🚻") # Header를 Subheader로 변경하여 축소
col_m, col_f = st.sidebar.columns(2)

with col_m:
    # 레이블 축소 및 가로 배치
    male_checked = st.checkbox('남자', key='male_check', value=True, help='남자 학교 (남고, 공학) 포함')
with col_f:
    # 레이블 축소 및 가로 배치
    female_checked = st.checkbox('여자', key='female_check', value=True, help='여자 학교 (여고, 공학) 포함')

# 사용자 요청 로직 적용:
if male_checked and female_checked:
    selected_coed = ['남여공학']
    coed_status_text = "남녀공학"
elif male_checked and not female_checked:
    selected_coed = ['남']
    coed_status_text = "남자 학교 (남고)"
elif not male_checked and female_checked:
    selected_coed = ['여']
    coed_status_text = "여자 학교 (여고)"
else:
    selected_coed = df_unique['남녀공학구분명'].unique().tolist()
    coed_status_text = "모든 성별 구분 (필터 해제됨)"

# 적용된 필터 상태를 caption으로 간결하게 표시
st.sidebar.caption(f"**필터 적용:** `{coed_status_text}`")
st.sidebar.markdown("---")
# --- ------------------------------- ---

# 4. 설립일자 범위 필터
min_date = df_unique['설립일자'].min().date()
max_date = df_unique['설립일자'].max().date()
selected_date_range = st.sidebar.date_input("설립일자 범위 선택", value=(min_date, max_date), min_value=min_date, max_value=max_date, format="YYYY.MM.DD")

# 5. 학교명 검색
search_term = st.sidebar.text_input('학교명 검색')


# --- 그래프 설정 ---
st.sidebar.markdown("---")
st.sidebar.header("그래프 설정 📊")

# 1. 학교 종류별 그래프 선택
chart_style_type = st.sidebar.selectbox(
    "1. 학교 종류별 그래프",
    ('가로 막대 그래프', '파이 차트'),
    key='chart_type_select'
)

# 2. 남녀공학별 그래프 선택
chart_style_coed = st.sidebar.selectbox(
    "2. 남녀공학별 그래프",
    ('세로 막대 그래프', '파이 차트'),
    key='chart_coed_select'
)

# 3. 설립 연도별 그래프 선택
chart_style_year = st.sidebar.selectbox(
    "3. 설립 연도별 그래프 (전체)",
    ('라인 차트', '막대 차트', '영역 차트'),
    key='chart_year_select'
)

# --- 공통 데이터 처리 (필터 적용) ---

if len(selected_date_range) == 2:
    start_date, end_date = selected_date_range
    # 날짜 필터링 시, start_date와 end_date가 포함되도록 비교
    date_filter = (df_unique['설립일자'].dt.date >= start_date) & (df_unique['설립일자'].dt.date <= end_date)
else:
    date_filter = pd.Series(True, index=df_unique.index)

# 필터링된 데이터프레임
df_filtered = df_unique[
    (df_unique['학교종류명'].isin(selected_types)) &
    (df_unique['설립구분'].isin(selected_establishments)) &
    (df_unique['남녀공학구분명'].isin(selected_coed)) & # 새롭게 계산된 selected_coed 사용
    (date_filter)
]

if search_term:
    df_filtered = df_filtered[df_filtered['학교명'].str.contains(search_term, na=False)]

# '설립연도' 컬럼 추가 (그래프 페이지에서 사용)
df_filtered = df_filtered.copy()
df_filtered['설립연도'] = df_filtered['설립일자'].dt.year

# --- 공통 KPI 계산 ---
total_school_count = df_filtered.shape[0]
public_count = df_filtered[df_filtered['설립구분'] == '공립'].shape[0]
private_count = df_filtered[df_filtered['설립구분'] == '사립'].shape[0]


# --- 메인 페이지 (타이틀) ---
st.title("🏫 서울시 구로구 학교 기본정보 대시보드")
st.write(f"현재 **'{page_selection}'** 페이지를 보고 있습니다.")
st.markdown("---")


# --- 페이지 분기 처리 ---

if page_selection == '그래프 분석':
    
    # --- 요약 현황 ---
    st.header("요약 현황 (사이드바 필터 적용됨)")
    col1, col2, col3 = st.columns(3)
    col1.metric("총 학교 수", f"{total_school_count} 개교")
    col2.metric("공립 학교", f"{public_count} 개교")
    col3.metric("사립 학교", f"{private_count} 개교")

    st.markdown("---")
    
    st.header("현황 그래프 (사이드바 필터 적용됨)")

    if df_filtered.empty:
        st.warning("사이드바 필터에 해당하는 데이터가 없습니다.")
    else:
        
        # --- 2열 레이아웃 ---
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            # --- 1. 학교 종류별 그래프 ---
            st.subheader("1. 학교 종류별 분포")
            chart_data_type = df_filtered['학교종류명'].value_counts().reset_index()
            chart_data_type.columns = ['학교종류명', '학교 수']

            if chart_style_type == '가로 막대 그래프':
                chart_type = alt.Chart(chart_data_type).mark_bar().encode(
                    x=alt.X('학교 수'),
                    y=alt.Y('학교종류명', sort='-x', title='학교 종류'),
                    color=alt.Color('학교종류명', legend=None),
                    tooltip=['학교종류명', '학교 수']
                ).properties(title='학교 종류별 분포').interactive()

            elif chart_style_type == '파이 차트':
                base = alt.Chart(chart_data_type).encode(
                    theta=alt.Theta("학교 수", stack=True)
                )
                pie = base.mark_arc(outerRadius=120).encode(
                    color=alt.Color("학교종류명"),
                    order=alt.Order("학교 수", sort="descending"),
                    tooltip=["학교종류명", "학교 수"]
                )
                text = base.mark_text(radius=140).encode(
                    text=alt.Text("학교 수", format=".0f"),
                    order=alt.Order("학교 수", sort="descending"),
                    color=alt.value("black")
                )
                chart_type = (pie + text).properties(title='학교 종류별 분포')
            
            st.altair_chart(chart_type, use_container_width=True)

        with col_chart2:
            # --- 2. 남녀공학 구분별 그래프 ---
            st.subheader("2. 남녀공학 구분별 분포")
            chart_data_coed = df_filtered['남녀공학구분명'].value_counts().reset_index()
            chart_data_coed.columns = ['남녀공학구분명', '학교 수']

            if chart_style_coed == '세로 막대 그래프':
                chart_coed = alt.Chart(chart_data_coed).mark_bar().encode(
                    x=alt.X('남녀공학구분명', sort='-y', title='성별 구분'),
                    y=alt.Y('학교 수'),
                    color=alt.Color('남녀공학구분명', legend=None),
                    tooltip=['남녀공학구분명', '학교 수']
                ).properties(title='남녀공학 구분별 분포').interactive()
            
            elif chart_style_coed == '파이 차트':
                base = alt.Chart(chart_data_coed).encode(
                    theta=alt.Theta("학교 수", stack=True)
                )
                pie = base.mark_arc(outerRadius=120).encode(
                    color=alt.Color("남녀공학구분명"),
                    order=alt.Order("학교 수", sort="descending"),
                    tooltip=["남녀공학구분명", "학교 수"]
                )
                text = base.mark_text(radius=140).encode(
                    text=alt.Text("학교 수", format=".0f"),
                    order=alt.Order("학교 수", sort="descending"),
                    color=alt.value("black")
                )
                chart_coed = (pie + text).properties(title='남녀공학 구분별 분포')
            
            st.altair_chart(chart_coed, use_container_width=True)

        
        st.markdown("---") # 다음 그래프와의 구분을 위한 선

        # --- 3. 설립 연도별 그래프 (전체 학교 수) ---
        st.subheader("3. 설립 연도별 학교 수 (전체)")
        chart_data_year = df_filtered.groupby('설립연도').size().reset_index(name='학교 수')

        # 연도별 차트의 기본 축 설정
        base_year = alt.Chart(chart_data_year).encode(
            x=alt.X('설립연도:Q', title='설립연도', axis=alt.Axis(format='d')), # :Q (Quantitative), 쉼표 없는 정수
            y=alt.Y('학교 수', title='설립된 학교 수'),
            tooltip=[alt.Tooltip('설립연도', format='d'), '학교 수']
        )

        if chart_style_year == '라인 차트':
            chart_year = base_year.mark_line(point=True).encode(color=alt.value("#4C78A8"))
        elif chart_style_year == '막대 차트':
            chart_year = base_year.mark_bar().encode(color=alt.value("#F58518"))
        elif chart_style_year == '영역 차트':
            chart_year = base_year.mark_area(opacity=0.7).encode(color=alt.value("#54A24B"))
        
        st.altair_chart(chart_year.properties(title='설립 연도별 학교 수').interactive(), use_container_width=True)
        
        st.markdown("---") # 다음 그래프와의 구분을 위한 선
        
        # --- 4. 설립 연도별 공립/사립 비율 그래프 ---
        st.subheader("4. 설립 연도별 공립 및 사립 학교 수 비교")
        
        # 4.1 데이터 준비: 설립연도별, 설립구분별 카운트
        chart_data_establishment_year = df_filtered.groupby(['설립연도', '설립구분']).size().reset_index(name='학교 수')

        # 4.2 Altair Stacked Bar Chart 생성
        chart_establishment_year = alt.Chart(chart_data_establishment_year).mark_bar().encode(
            # X-axis: 설립연도
            x=alt.X('설립연도:Q', title='설립연도', axis=alt.Axis(format='d')), 
            # Y-axis: 학교 수 (누적)
            y=alt.Y('학교 수', title='설립된 학교 수'),
            # Color: 설립구분 (공립/사립)
            color=alt.Color('설립구분', title='설립 구분'),
            # Tooltip
            tooltip=[alt.Tooltip('설립연도', format='d'), '설립구분', '학교 수']
        ).properties(
            title='설립 연도별 공립/사립 학교 설립 현황'
        ).interactive() # Allow zooming and panning

        st.altair_chart(chart_establishment_year, use_container_width=True)


elif page_selection == '학교 목록':
    
    # --- 상세 데이터 페이지 ---
    st.header(f"상세 학교 목록 ({total_school_count}개)")
    st.write("이 목록은 **사이드바 필터**의 영향을 받습니다.")

    columns_to_show = ['학교명', '학교종류명', '설립구분', '남녀공학구분명', '관할조직명', '설립일자']
    
    if df_filtered.empty:
        st.warning("사이드바 필터에 해당하는 데이터가 없습니다.")
    else:
        st.dataframe(
            df_filtered[columns_to_show].reset_index(drop=True),
            column_config={
                "설립일자": st.column_config.DatetimeColumn("설립일자", format="YYYY-MM-DD")
            },
            use_container_width=True
        )

    with st.expander("원본 데이터 전체 보기 (Multi-index 포함)"):
        st.dataframe(df_raw, use_container_width=True)