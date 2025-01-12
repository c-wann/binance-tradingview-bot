import os
import logging
import asyncio
import azure.functions as func
import telegram
from binance.spot import Spot as Client
from binance.error import ClientError

# Constants
ORDER_TYPE_LIMIT = "LIMIT"
TIME_IN_FORCE_GTC = "GTC"

lock = asyncio.Lock()

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

def get_json_body(req: func.HttpRequest):
    try:
        return req.get_json()
    except ValueError:
        logging.error("Invalid JSON body")
        return None

def place_order_sync(client, params):
    logging.info('place order...')
    return client.new_order(**params)

async def place_order(client, params):
    async with lock:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, place_order_sync, client, params)

@app.route(route="http_bnb_limit_order")
async def http_bnb_limit_order(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('http_bnb_limit_order is running...')
    _body = get_json_body(req)

    if _body is not None:
        try:
            _quantity = round(float(_body['total']) / float(_body['price']), 4)
            params = {
                "symbol": _body['symbol'],
                "side": _body['side'],
                "type": ORDER_TYPE_LIMIT,
                "timeInForce": TIME_IN_FORCE_GTC,
                "quantity": str(_quantity),
                "price": _body['price'],
            }
            api_key = os.environ['api_key']
            api_secret = os.environ['api_secret']
            client = Client(api_key, api_secret)

            # Place the order
            logging.info(f"Placing order with params: {params}")
            response = await place_order(client, params)
            logging.info(f"Order response: {response}")

            return func.HttpResponse(f"{response}", status_code=200)

        except ClientError as ce:
            logging.error(f"Binance client error: {ce}")
            return func.HttpResponse(f"Client error: {str(ce)}", status_code=500)
        except asyncio.TimeoutError:
            logging.error("API call timed out")
            return func.HttpResponse("Error: API call timed out", status_code=504)
        except Exception as e:
            logging.error(f"Error during processing: {e}")
            return func.HttpResponse(f"Error: {str(e)}", status_code=500)
    else:
        return func.HttpResponse("Error: No valid parameters provided", status_code=400)