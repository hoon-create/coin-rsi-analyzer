import requests
import pandas as pd

# 한글 이름 → 영문 심볼 매핑 사전
coin_name_to_symbol = {
    '비트코인': 'BTC',
    '이더리움': 'ETH',
    '도지코인': 'DOGE',
    '리플': 'XRP',
    '에이다': 'ADA',
    '솔라나': 'SOL',
    '온도파이낸스': 'ONDO',
    # 필요한 코인 더 추가 가능
}

# 업비트 전체 마켓 목록 조회 함수
def get_all_markets():
    url = "https://api.upbit.com/v1/market/all"
    response = requests.get(url)
    markets = response.json()
    krw_markets = [m['market'] for m in markets if m['market'].startswith('KRW-')]
    return krw_markets

# 코인명 입력 → 마켓코드 반환 함수
def find_market_code(user_input):
    symbol = coin_name_to_symbol.get(user_input, user_input.upper())
    market_list = get_all_markets()
    for market in market_list:
        if market == f"KRW-{symbol}":
            return market
    return None

# 캔들 데이터 가져오기
def get_candle_data(market_code):
    url = "https://api.upbit.com/v1/candles/minutes/5"
    params = {"market": market_code, "count": 200}
    headers = {"Accept": "application/json"}
    res = requests.get(url, params=params, headers=headers)
    if res.status_code == 200:
        data = res.json()
        df = pd.DataFrame(data)
        df['candle_date_time_kst'] = pd.to_datetime(df['candle_date_time_kst'])
        df.set_index('candle_date_time_kst', inplace=True)
        df = df[['opening_price', 'high_price', 'low_price', 'trade_price', 'candle_acc_trade_volume']]
        df.rename(columns={
            'opening_price': 'Open',
            'high_price': 'High',
            'low_price': 'Low',
            'trade_price': 'Close',
            'candle_acc_trade_volume': 'Volume'
        }, inplace=True)
        return df
    else:
        print("데이터 가져오기 실패:", res.status_code)
        return None

# RSI 계산
def calculate_rsi(df, period=14):
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# 이동평균선 추가
def add_moving_averages(df):
    df['MA_5'] = df['Close'].rolling(window=5).mean()
    df['MA_20'] = df['Close'].rolling(window=20).mean()

# MACD 계산
def calculate_macd(df, short=12, long=26, signal=9):
    short_ema = df['Close'].ewm(span=short, adjust=False).mean()
    long_ema = df['Close'].ewm(span=long, adjust=False).mean()
    macd = short_ema - long_ema
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    df['MACD'] = macd
    df['Signal'] = signal_line

# 결과 출력
def print_analysis(df):
    latest = df.iloc[-1]
    print("\n📊 최신 분석 결과:")
    print(f"- 현재가: {latest['Close']:.2f}원")
    print(f"- RSI: {latest['RSI']:.2f} {'(과매수)' if latest['RSI'] > 70 else '(과매도)' if latest['RSI'] < 30 else ''}")
    print(f"- MA(5): {latest['MA_5']:.2f}, MA(20): {latest['MA_20']:.2f}")
    if latest['MA_5'] > latest['MA_20']:
        print("  → 단기 상승세 (정배열)")
    elif latest['MA_5'] < latest['MA_20']:
        print("  → 단기 하락세 (역배열)")
    else:
        print("  → MA 정체 상태")
    if latest['MACD'] > latest['Signal']:
        print(f"- MACD: 상승 추세 (MACD > Signal)")
    else:
        print(f"- MACD: 하락 추세 (MACD < Signal)")

# 메인 실행
if __name__ == "__main__":
    coin = input("분석할 코인명을 입력하세요 (예: 도지코인 또는 DOGE): ")
    market_code = find_market_code(coin)
    if market_code:
        df = get_candle_data(market_code)
        if df is not None:
            df['RSI'] = calculate_rsi(df)
            add_moving_averages(df)
            calculate_macd(df)
            print_analysis(df)
        else:
            print("❌ 데이터 불러오기 실패")
    else:
        print("❌ 해당 코인을 찾을 수 없습니다.")
