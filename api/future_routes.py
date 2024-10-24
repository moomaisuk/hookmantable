from flask import Blueprint, jsonify
import json, math, env
import os
import requests

from flask import Flask, request
from binance.client import Client
from binance.enums import *

# Create a Blueprint instance for the 'ok' API
future_blueprint = Blueprint('future_blueprint', __name__)

@future_blueprint.route('/', methods=['GET'])
def future_home():
    return jsonify({"message": "Hello"})

@future_blueprint.route('/future/portfolio', methods=['GET'])
def future_portfolio():
    """
        http://{HOST_NAME}/api/future/portfolio?ACCESS_TOKEN={ACCESS_TOKEN}
        http://{HOST_NAME}/api/future/portfolio?ENV=prod&ACCESS_TOKEN={ACCESS_TOKEN}
    """
    ac_token = request.args.get('ACCESS_TOKEN')
    asset_env = request.args.get('ENV')

    if ac_token is None or ac_token != env.THIS_API_KEY:
        return jsonify({"message": 'Access denial'})

    try:
        if asset_env == "prod":
            client = Client(env.API_KEY, env.API_SECRET, tld='com')
            client.FUTURES_URL = env.FUTURES_URL[0]
        else:
            client = Client(env.FUTURES_API_KEY_TEST, env.FUTURES_API_SECRET_TEST, tld='com')
            client.FUTURES_URL = env.FUTURES_TESTNET_URL[0]
        return jsonify({"message": format(client.futures_account_balance())}) 
    except Exception as e:
        return jsonify({
            "error": f'portfolio: {format(e)}'
        })


@future_blueprint.route('/future/areyouok', methods=['GET'])
def future_areyouok():
    """
        http://{HOST_NAME}/api/future/areyouok?ACCESS_TOKEN={ACCESS_TOKEN}
        http://{HOST_NAME}/api/future/areyouok?ENV=prod&ACCESS_TOKEN={ACCESS_TOKEN}
    """
    ac_token = request.args.get('ACCESS_TOKEN')
    asset_env = request.args.get('ENV')

    if ac_token is None or ac_token != env.THIS_API_KEY:
        return jsonify({"message": 'Access denial'})

    try:
        if asset_env == "prod":
            client = Client(env.API_KEY, env.API_SECRET, tld='com')
            client.FUTURES_URL = env.FUTURES_URL[0]
        else:
            client = Client(env.FUTURES_API_KEY_TEST, env.FUTURES_API_SECRET_TEST, tld='com')
            client.FUTURES_URL = env.FUTURES_TESTNET_URL[0]

        return jsonify({
            'code': 'success',
            'data': {
                'server_ping': f'ping: {client.FUTURES_URL} => {client.ping()}'
            }
        }) 

    except Exception as e:
        return jsonify({
            "error": f'areyouok: {format(e)}'
        })

@future_blueprint.route('/future/trade', methods=['POST'])
def future_trade():
    """
        curl -X POST "http://{HOST_NAME}/api/future/trade"^
            -H "Authorization: {ACCESS_TOKEN}" ^
            -H "Content-Type: application/json" ^
            -d "{\"system\": \"Long and Short future\", \"passphrase\": \"joe-kaiten-mawashi-geri\", \"time\": \"22 Jan 2023\", \"QTY_Type\": \"FINAL\", \"exchange\": \"Binance\", \"ticker\": \"BTCUSDT\", \"bar\": { \"time\": \"9:00\", \"open\": 10000, \"high\": 12000, \"low\": 8000, \"close\": 11000, \"volume\": 100 }, \"strategy\": { \"SIDE\": \"BUY\", \"QTY\": \"5%\", \"LEVERAGE\": \"1\" }}"
        curl -X POST "http://{HOST_NAME}/api/future/trade?ENV=prod"^
            -H "Authorization: {ACCESS_TOKEN}" ^
            -H "Content-Type: application/json" ^
            -d "{\"system\": \"Long and Short future\", \"passphrase\": \"joe-kaiten-mawashi-geri\", \"time\": \"22 Jan 2023\", \"QTY_Type\": \"FINAL\", \"exchange\": \"Binance\", \"ticker\": \"BTCUSDT\", \"bar\": { \"time\": \"9:00\", \"open\": 10000, \"high\": 12000, \"low\": 8000, \"close\": 11000, \"volume\": 100 }, \"strategy\": { \"SIDE\": \"BUY\", \"QTY\": \"5%\", \"LEVERAGE\": \"1\" }}"
        
    """
    ac_token = request.headers.get('Authorization')
    asset_env = request.args.get('ENV')

    if ac_token is None or ac_token != env.THIS_API_KEY:
        return jsonify({"message": 'Access denial'})

    # check Data Format
    try:
        data = json.loads(request.data)
        symbol = data["ticker"]
        strategy = data['strategy']
        side = strategy['SIDE'].upper()
    except Exception as e:
        return jsonify({
            "error": f'check Data Format: {format(e)}'
        })
    
    # check Pass phrase
    if data['passphrase'] != env.THIS_WEBHOOK_PASSPHRASE:
        return jsonify({
            "error": f'check Pass phrase: Invalid passphrase'
        })

    # check TEST or ACTUAL trade
    if asset_env == "prod":
        client = Client(env.API_KEY, env.API_SECRET, tld='com')
        client.FUTURES_URL = env.FUTURES_URL[0]
    else:
        client = Client(env.FUTURES_API_KEY_TEST, env.FUTURES_API_SECRET_TEST, tld='com')
        client.FUTURES_URL = env.FUTURES_TESTNET_URL[0]

    # check qty type (Percentage or unit)
    try:
        if strategy['QTY'][-1] == "%":
            percentage_port_require = float(strategy['QTY'][:-1])/100
            URL = env.FUTURES_URL[0] + "/v1/ticker/24hr?symbol=" + symbol.upper() # https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=BTCUSDT
            last_price = float(requests.get(URL).json()['lastPrice'])
            require_qty_raw = get_cash(client)[0] * percentage_port_require / last_price
        elif 'USDT' in strategy['QTY']:
            URL = env.FUTURES_URL[0] + "/v1/ticker/24hr?symbol=" + symbol.upper()
            last_price = float(requests.get(URL).json()['lastPrice'])
            require_qty_raw = float(strategy['QTY'][:-4]) / last_price
        else:
            require_qty_raw = float(strategy['QTY'])
    except Exception as e:
        return jsonify({
            "error": f'check qty type: {format(e)}'
        })
    
    # Set leverage
    try:
        leverage_setup = round(float(strategy['LEVERAGE']))
    except:
        leverage_setup = 1

    try:
        client.futures_change_leverage(symbol = symbol, leverage = leverage_setup)
        require_qty_raw = require_qty_raw * leverage_setup
    except Exception as e:
        return jsonify({
            "error": f'check qty type: {format(e)}'
        })

    # Round Decimal of symbol
    for i in client.futures_exchange_info()["symbols"]:
        if i['symbol'] == symbol:
            precision =  int(i['quantityPrecision'])
            break
    if side == "SELL":
        require_qty_raw = -require_qty_raw

    # make order
    try:
        QuantityType = data["QTY_Type"].upper()
    except:
        QuantityType = "ACTUAL"
    
    try:
        if QuantityType == "FINAL":
            action_amount = require_qty_raw - get_existing_amount(symbol, client)
            action_amount = round_decimals_down(action_amount, precision)
            if action_amount > 0:
                order = trade_order(symbol, "BUY", abs(action_amount), client)
            elif action_amount < 0:
                order = trade_order(symbol, "SELL", abs(action_amount), client)
            else:
                order = trade_order(symbol, side, abs(action_amount), client)
        else:
            require_qty = round_decimals_down(require_qty_raw, precision)
            order = trade_order(symbol, side, abs(require_qty), client)
    except:
        return {
            "code": "error",
            "message": "Cannot make order"
        }
    
    line(order['message'])
    return(order)

# -------------------------------------------UTILS
def line(msg):
    try:
        url = env.LINE_NOTI_URL[0]
        token = env.LINE_NOTI_TOKEN
        headers = {'content-type': 'application/x-www-form-urlencoded', 'Authorization': 'Bearer ' + token}
        r = requests.post(url, headers=headers, data={'message': msg})
    except Exception as e:
        return jsonify({
            "error": f'line: {format(e)}'
        })

def round_decimals_down(number:float, decimals:int=2):
    """
    Returns a value rounded down to a specific number of decimal places.
    """
    if not isinstance(decimals, int):
        raise TypeError("decimal places must be an integer")
    elif decimals < 0:
        raise ValueError("decimal places has to be 0 or more")
    elif decimals == 0:
        return math.floor(number)

    factor = 10 ** decimals
    return math.floor(number * factor) / factor

def get_existing_amount(symbol, client):
    i = float(client.futures_position_information(symbol = symbol)[-1]['positionAmt'])
    return i

def get_cash(client):
    try:
        item = client.futures_account()
        balance = float(item['totalMarginBalance']) #all balance
        cash = float(item['totalCrossWalletBalance']) - float(item['totalInitialMargin']) #cross wallet balance - all margin
        return balance, cash
    except Exception as e:
        return jsonify({
            "error": f'get_cash: {format(e)}'
        })
    
def trade_order(symbol, side, qty, client):
    try:
        order = client.futures_create_order(
            symbol=symbol,
            side=side,
            positionSide='BOTH',
            type='MARKET',
            quantity=qty
            )
        return {
            'status': "Success",
            'message' : format(order)
        }
    except Exception as e:
        return jsonify({
            "error": f'trade_order: {format(e)}'
        })



