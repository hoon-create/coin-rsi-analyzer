from flask import Flask, request, render_template_string
import requests
import pandas as pd

app = Flask(__name__)

coin_name_to_symbol = {
    '비트코인': 'BTC', '이더리움': 'ETH', '도지코인': 'DOGE',
    '리플': 'XRP', '에이다': 'ADA', '솔라나': 'SOL', '온도파이낸스': 'ONDO'
}

def get_all_markets():
    url = "https://api.upbit.com/v1/market/all"
    response = requests.get(url)
    markets = response.json()
    return [m['market'] for m in markets if m['market'].startswith('KRW-')]

def find_market_code(user_input):
    symbol = coin_name_to_symbol.get(user_input, user_input.upper())
    markets = get_all_markets()
    for market in markets:
        if market == f"KRW-{symbol}":
            return market
    return None

def get_candle_data(market_code):
    url = "https://api.upbit.com/v1/candles/minutes/5"
    params = {"market": market_code, "count": 200}
    res = requests.get(url, params=params)
    data = res.json()
    df = pd.DataFrame(data)
    df['Close'] = df['trade_price']
    df = df.iloc[::-1].reset_index(drop=True)  # 시간순 정렬
    return df

def calculate_rsi(df, period=14):
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_macd(df):
    short_ema = df['Close'].ewm(span=12, adjust=False).mean()
    long_ema = df['Close'].ewm(span=26, adjust=False).mean()
    macd = short_ema - long_ema
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal

@app.route('/', methods=['GET', 'POST'])
def index():
    result = ""
    if request.method == 'POST':
        coin_name = request.form['coin_name']
        market_code = find_market_code(coin_name)
        if market_code:
            df = get_candle_data(market_code)

            # 기술적 지표 계산
            df['RSI'] = calculate_rsi(df)
            df['MA5'] = df['Close'].rolling(window=5).mean()
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['MACD'], df['Signal'] = calculate_macd(df)

            # 최신값 추출
            latest = df.iloc[-1]
            close_price = latest['Close']
            rsi = latest['RSI']
            ma5 = latest['MA5']
            ma20 = latest['MA20']
            macd = latest['MACD']
            signal = latest['Signal']

            result = f"""
            <h3>📊 {coin_name}의 기술적 분석 결과</h3>
            <ul>
                <li>현재 가격: <b>{close_price:,.2f}원</b></li>
                <li>RSI (14): <b>{rsi:.2f}</b> ({'과매수' if rsi>70 else '과매도' if rsi<30 else '중립'})</li>
                <li>이동평균선(MA5): <b>{ma5:,.2f}</b></li>
                <li>이동평균선(MA20): <b>{ma20:,.2f}</b></li>
                <li>MACD: <b>{macd:.4f}</b></li>
                <li>Signal: <b>{signal:.4f}</b></li>
            </ul>
            """
        else:
            result = "❌ 코인명을 인식할 수 없습니다."

    return render_template_string("""
        <h2>📈 실시간 코인 종합 분석기</h2>
        <form method="post">
            <input name="coin_name" placeholder="예: 도지코인 또는 DOGE">
            <input type="submit" value="분석하기">
        </form>
        <div>{{result|safe}}</div>
    """, result=result)
import os

if __name__ == "__main__":
    from gunicorn.app.base import BaseApplication
    from gunicorn.six import iteritems

    class GunicornApp(BaseApplication):
        def __init__(self, app):
            self.application = app
            super(GunicornApp, self).__init__()

        def load(self):
            return self.application

    GunicornApp(app).run()
