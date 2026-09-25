import concurrent.futures
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
import yfinance as yf
from bs4 import BeautifulSoup
from streamlit_autorefresh import st_autorefresh
import FinanceDataReader as fdr

# --- 1. 페이지 설정 및 보안(비밀번호) 인증 ---
st.set_page_config(
    page_title="계좌별 포트폴리오 및 시장 지수 대시보드",
    page_icon="📈",
    layout="wide",
)

# 🔒 [보안] 비밀번호 기능 추가
USER_PASSWORD = "102938"  # <--- 원하시는 비밀번호로 변경하여 사용하세요!
input_pw = st.sidebar.text_input(
    "🔑 대시보드 비밀번호를 입력하세요:", type="password"
)

if input_pw != USER_PASSWORD:
  st.warning("🔒 비밀번호를 올바르게 입력해야 접속할 수 있습니다.")
  st.stop()  # 비밀번호가 틀리거나 미입력 시 아래 코드를 실행하지 않고 멈춤

# --- 비밀번호 인증 성공 후 아래 코드 실행 ---

# 60초(1분)마다 화면 자동 새로고침
st_autorefresh(interval=60000, key="portfolio_autorefresh")

# --- 2. 실시간 시장 지수 / 환율 / 금리 데이터 수집 ---
st.title("📊 주요 시장 지수 및 금리/환율 현황")


@st.cache_data(ttl=60)
def get_market_data():
  results = {}

  # 1) 코스피 지수 (^KS11)
  try:
    kospi = yf.Ticker("^KS11")
    hist = kospi.history(period="5d")
    if not hist.empty and len(hist) >= 2:
      latest = float(hist["Close"].iloc[-1])
      prev = float(hist["Close"].iloc[-2])
      change = latest - prev
      change_pct = (change / prev) * 100
      results["코스피 지수"] = {
          "price": latest,
          "change": change,
          "change_pct": change_pct,
      }
    else:
      results["코스피 지수"] = None
  except Exception:
    results["코스피 지수"] = None

  # 2) 환율
  fx_configs = [
      ("원/달러 환율", "KRW=X", 1),  # 달러당 원화
      ("원/엔 환율 (100엔)", "JPYKRW=X", 100),  # 100엔당 원화
  ]

  for fx_name, yf_code, scale in fx_configs:
    try:
      stock = yf.Ticker(yf_code)
      hist = stock.history(period="5d")
      if not hist.empty and len(hist) >= 2:
        latest = float(hist["Close"].iloc[-1]) * scale
        prev = float(hist["Close"].iloc[-2]) * scale
        change = latest - prev
        results[fx_name] = {"price": latest, "change": change}
      else:
        results[fx_name] = None
    except Exception:
      results[fx_name] = None

  # 3) 미국 S&P 500, 나스닥 100, 미국채 금리
  yf_targets = {
      "S&P 500": "^GSPC",
      "나스닥 100": "^NDX",
      "미국 10년물 국채 금리": "^TNX",
      "미국 30년물 국채 금리": "^TYX",
  }

  for name, ticker in yf_targets.items():
    try:
      stock = yf.Ticker(ticker)
      df = stock.history(period="5d")
      if not df.empty and len(df) >= 2:
        latest = float(df["Close"].iloc[-1])
        prev = float(df["Close"].iloc[-2])
        change = latest - prev
        change_pct = (change / prev) * 100 if prev != 0 else 0
        results[name] = {
            "price": latest,
            "change": change,
            "change_pct": change_pct,
        }
      else:
        results[name] = None
    except Exception:
      results[name] = None

  # 4) 한국 10년물 국채 금리
  try:
    kr_10y = fdr.DataReader("KR10YT=RR")
    if not kr_10y.empty:
      latest = float(kr_10y["Close"].iloc[-1])
      prev = (
          float(kr_10y["Close"].iloc[-2]) if len(kr_10y) > 1 else latest
      )
      change = latest - prev
      results["한국 10년물 국채 금리"] = {
          "price": latest,
          "change": change,
      }
    else:
      results["한국 10년물 국채 금리"] = None
  except Exception:
    results["한국 10년물 국채 금리"] = None

  return results


with st.spinner("시장 실시간 데이터를 불러오는 중입니다..."):
  market_results = get_market_data()

# 지수 & 환율 (1행 4열)
col1, col2, col3, col4 = st.columns(4)

if market_results.get("코스피 지수"):
  d = market_results["코스피 지수"]
  col1.metric("코스피", f"{d['price']:,.2f} pt", f"{d['change_pct']:+.2f}%")
else:
  col1.metric("코스피", "데이터 없음")

if market_results.get("S&P 500"):
  d = market_results["S&P 500"]
  col2.metric("S&P 500", f"{d['price']:,.2f} pt", f"{d['change_pct']:+.2f}%")

if market_results.get("나스닥 100"):
  d = market_results["나스닥 100"]
  col3.metric("나스닥 100", f"{d['price']:,.2f} pt", f"{d['change_pct']:+.2f}%")

if market_results.get("원/달러 환율"):
  d = market_results["원/달러 환율"]
  col4.metric(
      "원/달러 환율", f"{d['price']:,.2f} 원", f"{d['change']:+.2f} 원"
  )
else:
  col4.metric("원/달러 환율", "데이터 없음")

# 금리 & 엔화 환율 (2행 4열)
col5, col6, col7, col8 = st.columns(4)

if market_results.get("원/엔 환율 (100엔)"):
  d = market_results["원/엔 환율 (100엔)"]
  col5.metric(
      "원/100엔 환율", f"{d['price']:,.2f} 원", f"{d['change']:+.2f} 원"
  )
else:
  col5.metric("원/100엔 환율", "데이터 없음")

if market_results.get("미국 10년물 국채 금리"):
  d = market_results["미국 10년물 국채 금리"]
  col6.metric(
      "미국 10년물 금리", f"{d['price']:.3f} %", f"{d['change']:+.3f}%p"
  )

if market_results.get("미국 30년물 국채 금리"):
  d = market_results["미국 30년물 국채 금리"]
  col7.metric(
      "미국 30년물 금리", f"{d['price']:.3f} %", f"{d['change']:+.3f}%p"
  )

if market_results.get("한국 10년물 국채 금리"):
  d = market_results["한국 10년물 국채 금리"]
  col8.metric(
      "한국 10년물 금리", f"{d['price']:.3f} %", f"{d['change']:+.3f}%p"
  )

st.divider()

# --- 3. 하단: 나의 포트폴리오 데이터 설정 ---
isa_portfolio = [
    {
        "ticker": "005389",
        "name": "현대차3우B",
        "avg_price": 223985,
        "quantity": 28,
        "category": "국내주식",
    },
    {
        "ticker": "071055",
        "name": "한국금융지주우",
        "avg_price": 164185,
        "quantity": 85,
        "category": "국내주식",
    },
    {
        "ticker": "003475",
        "name": "유안타증권우",
        "avg_price": 4282,
        "quantity": 450,
        "category": "국내주식",
    },
    {
        "ticker": "0098N0",
        "name": "PLUS자사주매입고배당주",
        "avg_price": 13362,
        "quantity": 920,
        "category": "국내지수 ETF",
    },
    {
        "ticker": "329200",
        "name": "TIGER리츠부동산인프라",
        "avg_price": 4246,
        "quantity": 310,
        "category": "리츠",
    },
    {
        "ticker": "069500",
        "name": "KODEX200(7900)",
        "avg_price": 125217,
        "quantity": 17,
        "category": "국내지수 ETF",
    },
    {
        "ticker": "152100",
        "name": "PLUS200(7880)",
        "avg_price": 126865,
        "quantity": 16,
        "category": "국내지수 ETF",
    },
    {
        "ticker": "105190",
        "name": "ACE200(7810)",
        "avg_price": 123823,
        "quantity": 17,
        "category": "국내지수 ETF",
    },
    {
        "ticker": "102110",
        "name": "TIGER200(7800)",
        "avg_price": 123962,
        "quantity": 17,
        "category": "국내지수 ETF",
    },
    {
        "ticker": "122090",
        "name": "PLUS코스피50(7350)",
        "avg_price": 87776,
        "quantity": 9,
        "category": "국내지수 ETF",
    },
    {
        "ticker": "237350",
        "name": "KODEX코스피100(7300)",
        "avg_price": 92649,
        "quantity": 8,
        "category": "국내지수 ETF",
    },
    {
        "ticker": "277640",
        "name": "TIGER코스피대형주(7270)",
        "avg_price": 39822,
        "quantity": 13,
        "category": "국내지수 ETF",
    },
    {
        "ticker": "337140",
        "name": "KODEX코스피대형주(7240)",
        "avg_price": 38421,
        "quantity": 14,
        "category": "국내지수 ETF",
    },
    {
        "ticker": "302450",
        "name": "RISE코스피(7230)",
        "avg_price": 75063,
        "quantity": 8,
        "category": "국내지수 ETF",
    },
    {
        "ticker": "305050",
        "name": "ACE코스피(7150)",
        "avg_price": 74304,
        "quantity": 8,
        "category": "국내지수 ETF",
    },
    {
        "ticker": "277630",
        "name": "TIGER코스피(6965)",
        "avg_price": 72739,
        "quantity": 7,
        "category": "국내지수 ETF",
    },
    {
        "ticker": "226490",
        "name": "KODEX코스피(6960)",
        "avg_price": 71678,
        "quantity": 8,
        "category": "국내지수 ETF",
    },
    {
        "ticker": "153270",
        "name": "KIWOOM코스피100(6230)",
        "avg_price": 76743,
        "quantity": 3,
        "category": "국내지수 ETF",
    },
    {
        "ticker": "360200",
        "name": "ACE미국S&P500",
        "avg_price": 27247,
        "quantity": 16,
        "category": "해외지수 ETF",
    },
    {
        "ticker": "360750",
        "name": "TIGER미국S&P500",
        "avg_price": 26533,
        "quantity": 14,
        "category": "해외지수 ETF",
    },
    {
        "ticker": "379780",
        "name": "RISE미국S&P500",
        "avg_price": 22864,
        "quantity": 10,
        "category": "해외지수 ETF",
    },
    {
        "ticker": "449180",
        "name": "KODEX미국S&P500(H)",
        "avg_price": 17230,
        "quantity": 12,
        "category": "해외지수 ETF",
    },
    {
        "ticker": "368590",
        "name": "RISE미국나스닥100",
        "avg_price": 30806,
        "quantity": 17,
        "category": "해외지수 ETF",
    },
    {
        "ticker": "367380",
        "name": "ACE미국나스닥100",
        "avg_price": 31497,
        "quantity": 13,
        "category": "해외지수 ETF",
    },
    {
        "ticker": "379810",
        "name": "KODEX미국나스닥100",
        "avg_price": 26607,
        "quantity": 10,
        "category": "해외지수 ETF",
    },
    {
        "ticker": "449190",
        "name": "KODEX미국나스닥100(H)",
        "avg_price": 22180,
        "quantity": 11,
        "category": "해외지수 ETF",
    },
    {
        "ticker": "458730",
        "name": "TIGER미국배당다우존스",
        "avg_price": 15042,
        "quantity": 31,
        "category": "해외지수 ETF",
    },
    {
        "ticker": "475350",
        "name": "RISE버크셔포트폴리오TOP10",
        "avg_price": 14721,
        "quantity": 48,
        "category": "해외지수 ETF",
    },
    {
        "ticker": "455030",
        "name": "KODEX미국달러SOFR금리액티브(합성)",
        "avg_price": 11906,
        "quantity": 13,
        "category": "채권/파킹 ETF",
    },
    {
        "ticker": "455960",
        "name": "RISE미국달러SOFR금리액티브(합성)",
        "avg_price": 12161,
        "quantity": 12,
        "category": "채권/파킹 ETF",
    },
    {
        "ticker": "456880",
        "name": "ACE미국달러SOFR금리(합성)",
        "avg_price": 12564,
        "quantity": 31,
        "category": "채권/파킹 ETF",
    },
    {
        "ticker": "411060",
        "name": "ACEKRX 금현물",
        "avg_price": 26496,
        "quantity": 4,
        "category": "원자재",
    },
    {
        "ticker": "468380",
        "name": "KODEXiShares미국하이일드액티브",
        "avg_price": 11037,
        "quantity": 15,
        "category": "채권/파킹 ETF",
    },
    {
        "ticker": "484790",
        "name": "KODEX미국30년국채액티브(H)",
        "avg_price": 8200,
        "quantity": 12,
        "category": "채권/파킹 ETF",
    },
]

pension_portfolio = [
    {
        "ticker": "0098N0",
        "name": "PLUS자사주매입고배당주",
        "avg_price": 13078,
        "quantity": 675,
        "category": "국내지수 ETF",
    },
    {
        "ticker": "329200",
        "name": "TIGER리츠부동산인프라",
        "avg_price": 4249,
        "quantity": 301,
        "category": "리츠",
    },
    {
        "ticker": "069500",
        "name": "KODEX200(7260)",
        "avg_price": 115070,
        "quantity": 3,
        "category": "국내지수 ETF",
    },
    {
        "ticker": "152100",
        "name": "PLUS200(7085)",
        "avg_price": 114095,
        "quantity": 1,
        "category": "국내지수 ETF",
    },
    {
        "ticker": "105190",
        "name": "ACE200(7285)",
        "avg_price": 115513,
        "quantity": 3,
        "category": "국내지수 ETF",
    },
    {
        "ticker": "102110",
        "name": "TIGER200(7260)",
        "avg_price": 115183,
        "quantity": 3,
        "category": "국내지수 ETF",
    },
    {
        "ticker": "360200",
        "name": "ACE미국S&P500",
        "avg_price": 26518,
        "quantity": 9,
        "category": "해외지수 ETF",
    },
    {
        "ticker": "449180",
        "name": "KODEX미국S&P500(H)",
        "avg_price": 17145,
        "quantity": 3,
        "category": "해외지수 ETF",
    },
    {
        "ticker": "368590",
        "name": "RISE미국나스닥100",
        "avg_price": 30183,
        "quantity": 7,
        "category": "해외지수 ETF",
    },
    {
        "ticker": "449190",
        "name": "KODEX미국나스닥100(H)",
        "avg_price": 22359,
        "quantity": 4,
        "category": "해외지수 ETF",
    },
    {
        "ticker": "475350",
        "name": "RISE버크셔포트폴리오TOP10",
        "avg_price": 14684,
        "quantity": 24,
        "category": "해외지수 ETF",
    },
    {
        "ticker": "455030",
        "name": "KODEX미국달러SOFR금리액티브(합성)",
        "avg_price": 12005,
        "quantity": 5,
        "category": "채권/파킹 ETF",
    },
    {
        "ticker": "455960",
        "name": "RISE미국달러SOFR금리액티브(합성)",
        "avg_price": 12276,
        "quantity": 12,
        "category": "채권/파킹 ETF",
    },
    {
        "ticker": "456880",
        "name": "ACE미국달러SOFR금리(합성)",
        "avg_price": 12713,
        "quantity": 31,
        "category": "채권/파킹 ETF",
    },
    {
        "ticker": "455660",
        "name": "ACE미국하이일드액티브(H)",
        "avg_price": 9708,
        "quantity": 26,
        "category": "채권/파킹 ETF",
    },
    {
        "ticker": "484790",
        "name": "KODEX미국30년국채액티브(H)",
        "avg_price": 8178,
        "quantity": 6,
        "category": "채권/파킹 ETF",
    },
]

# --- 4. 사이드바 메뉴 ---
st.sidebar.title("📌 계좌 선택")
selected_account = st.sidebar.radio(
    "조회할 계좌를 선택하세요:", ("ISA 계좌", "연금 계좌")
)

if selected_account == "ISA 계좌":
  current_portfolio = isa_portfolio
  page_title = "🏢 ISA 계좌 포트폴리오"
else:
  current_portfolio = pension_portfolio
  page_title = "🏦 연금 계좌 포트폴리오"

st.subheader(page_title)


# --- 5. 병렬 처리로 모든 종목 실시간 가격 한 번에 수집 ---
@st.cache_data(ttl=60)
def get_all_prices_parallel(tickers):
  def fetch(ticker):
    try:
      df_stock = fdr.DataReader(ticker)
      if not df_stock.empty:
        return ticker, float(df_stock["Close"].iloc[-1])
    except:
      pass

    headers = {"User-Agent": "Mozilla/5.0"}
    try:
      url = f"https://finance.naver.com/item/main.naver?code={ticker}"
      res = requests.get(url, headers=headers, timeout=5)
      soup = BeautifulSoup(res.text, "html.parser")
      price_elem = soup.select_one("p.no_today .blind")
      if price_elem:
        return ticker, float(price_elem.text.replace(",", ""))
    except:
      pass

    return ticker, None

  prices = {}
  with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    future_to_ticker = {executor.submit(fetch, t): t for t in set(tickers)}
    for future in concurrent.futures.as_completed(future_to_ticker):
      t, p = future.result()
      prices[t] = p
  return prices


# --- 6. 계좌별 데이터 계산 ---
portfolio_data = []
total_invested = 0
total_current_value = 0

tickers_to_fetch = [item["ticker"] for item in current_portfolio]

with st.spinner("🚀 포트폴리오 주가 데이터를 고속(병렬)으로 불러오는 중입니다..."):
  prices_dict = get_all_prices_parallel(tickers_to_fetch)

for item in current_portfolio:
  ticker = item["ticker"]
  current_price = prices_dict.get(ticker)

  if current_price is None or pd.isna(current_price):
    current_price = item["avg_price"]

  avg_price = item["avg_price"]
  quantity = item["quantity"]

  invested = avg_price * quantity
  current_value = current_price * quantity
  profit_loss = current_value - invested
  return_rate = (profit_loss / invested) * 100 if invested > 0 else 0

  total_invested += invested
  total_current_value += current_value

  portfolio_data.append({
      "종목명": item["name"],
      "카테고리": item["category"],
      "티커": ticker,
      "보유수량": quantity,
      "평단가": avg_price,
      "현재가": current_price,
      "매수금액": invested,
      "평가금액": current_value,
      "수익금": profit_loss,
      "수익률": return_rate,
  })

df = pd.DataFrame(portfolio_data)

total_profit = total_current_value - total_invested
total_return_rate = (
    (total_profit / total_invested) * 100 if total_invested > 0 else 0
)

# --- 7. 자산 요약 메트릭 ---
st.markdown(f"### 💰 {selected_account} 자산 요약")
col1, col2, col3 = st.columns(3)

col1.metric("총 매수 금액", f"{total_invested:,.0f} 원")
col2.metric(
    "총 평가 금액", f"{total_current_value:,.0f} 원", f"{total_profit:+,.0f} 원"
)
col3.metric("총 수익률", f"{total_return_rate:.2f}%", f"{total_return_rate:+.2f}%")

st.divider()

# --- 8. Finviz 스타일 트리맵 ---
st.markdown(f"### 🗺️ {selected_account} 포트폴리오 맵")

if not df.empty:
  finviz_colors = [
      [0.0, "#B71C1C"],
      [0.2, "#E53935"],
      [0.35, "#EF5350"],
      [0.48, "#212121"],
      [0.5, "#1E1E1E"],
      [0.52, "#212121"],
      [0.65, "#66BB6A"],
      [0.8, "#4CAF50"],
      [1.0, "#1B5E20"],
  ]

  fig = px.treemap(
      df,
      path=[px.Constant(selected_account), "카테고리", "종목명"],
      values="평가금액",
      color="수익률",
      color_continuous_scale=finviz_colors,
      range_color=[-3.0, 3.0],
      color_continuous_midpoint=0,
      custom_data=["수익률", "평가금액", "수익금", "평단가", "현재가"],
  )

  fig.update_traces(
      texttemplate=(
          "<b>%{label}</b><br><span style='font-size: 13px;'>평단:"
          " %{customdata[3]:,.0f}원</span><br><span style='font-size: 15px;"
          " font-weight: bold;'>%{customdata[0]:+.2f}%</span>"
      ),
      hovertemplate=(
          "<b>%{label}</b><br>평단가: %{customdata[3]:,.0f}원<br>현재가:"
          " %{customdata[4]:,.0f}원<br>평가금액: %{customdata[1]:,.0f}원<br>수익금:"
          " %{customdata[2]:+,.0f}원<br>수익률: %{customdata[0]:+.2f}%"
      ),
      textfont=dict(
          size=15,
          family="Malgun Gothic, Apple SD Gothic Neo, sans-serif",
          color="white",
      ),
      marker=dict(cornerradius=2, line=dict(width=2, color="#000000")),
      selector=dict(type="treemap"),
  )

  fig.update_layout(
      margin=dict(t=30, l=10, r=10, b=10),
      height=780,
      paper_bgcolor="#111111",
      plot_bgcolor="#111111",
      font=dict(size=16, color="white"),
      coloraxis_colorbar=dict(title="수익률 (%)", ticksuffix="%", dtick=1.0),
  )

  st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- 사이드바 즉시 새로고침 버튼 ---
if st.sidebar.button("🔄 즉시 새로고침"):
  st.cache_data.clear()
  st.rerun()