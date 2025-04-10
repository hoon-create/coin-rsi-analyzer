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
    return df[::-1]  # 시간순 정렬

def calculate_rsi(df, period=14):
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

@app.route('/', methods=['GET', 'POST'])
def index():
    result = ""
    if request.method == 'POST':
        coin_name = request.form['coin_name']
        market_code = find_market_code(coin_name)
        if market_code:
            df = get_candle_data(market_code)
            df['RSI'] = calculate_rsi(df)
            rsi_now = df['RSI'].iloc[-1]
            result = f"<b>{coin_name}</b>의 RSI: {rsi_now:.2f}<br>"
            result += "💡 과매수 구간입니다!" if rsi_now > 70 else "💡 과매도 구간입니다!" if rsi_now < 30 else "⚖️ 중립 구간입니다."
        else:
            result = "❌ 코인명을 인식할 수 없습니다."
    return render_template_string("""
        <h2>📊 실시간 코인 RSI 분석기</h2>
        <form method="post">
            <input name="coin_name" placeholder="예: 도지코인 또는 DOGE">
            <input type="submit" value="분석하기">
        </form>
        <p>{{result|safe}}</p>
    """, result=result)
