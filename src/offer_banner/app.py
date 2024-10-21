import os
import json
import time
import redis
from flask import Flask, jsonify, render_template, request

from jaeger_client import Config
from flask_opentracing import FlaskTracing

app = Flask(__name__)

SELF_PORT = os.environ.get('SELF_PORT')

REDIS_PORT = os.environ.get('REDIS_PORT')
REDIS_HOST = os.environ.get('REDIS_HOST')
REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD')

JAEGER_AGENT_HOST = os.environ.get('JAEGER_AGENT_HOST')
JAEGER_AGENT_PORT = os.environ.get('JAEGER_AGENT_PORT')

r_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD)

def init_tracer():
    config = Config(
        config={
            'sampler': {
                'type': 'const',
                'param': 1,
            },
            'local_agent': {
                'reporting_host': JAEGER_AGENT_HOST,
                'reporting_port': JAEGER_AGENT_PORT,
            },
            'logging': True,
        },
        service_name='ms-offer-banner',
    )
    return config.initialize_tracer()

tracer = init_tracer()
tracing = FlaskTracing(tracer, True, app)

def trace_redis_operation(scope, operation: str, key: str, value: str = None):
    span = scope.span
    
    span.set_tag('cache.type', 'redis')
    span.set_tag('cache.operation', operation)
    span.set_tag('cache.key', key)
    
    if value:
        span.set_tag('cache.value', value)  # Optionally log value for 'set' operations
    
    span.log_kv({'key': key, 'value': value if value else 'N/A'})

# ================================================================================================ #

def redis_command(command, *args):
    max_retries = 3
    count = 0
    backoff_seconds = 5
    while True:
        try:
            return command(*args)
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
            count += 1
            if count > max_retries:
                raise
        print('Retrying in {} seconds'.format(backoff_seconds))
        time.sleep(backoff_seconds)


class Ad:
    def __init__(self, adID="", alt="", url="", category="", date="", time="") -> None:
        self.adID = adID
        self.alt = alt
        self.url = url
        self.category = category
        self.date = date
        self.time = time
        
@app.route('/', methods=['GET'])
@tracing.trace()
def index():
    with tracer.start_active_span('/offer-banner/') as scope:
        return render_template('index.html', r_client=r_client, REDIS_HOST=REDIS_HOST, REDIS_PORT=REDIS_PORT, REDIS_PASSWORD=REDIS_PASSWORD)


@app.route('/getAds', methods=['GET'])
@tracing.trace()
def getAds():
    with tracer.start_active_span('/offer-banner/getAds') as scope:
        ads = {}

        with tracer.start_active_span('redis_scan_iter') as redis_span:
            trace_redis_operation(redis_span, 'scan_iter', '*')
            adIDs = redis_command(r_client.scan_iter, "*")

        for adID in adIDs:
            ad = getAd(adID)
            if "adID" in ad:
                ads[ad["adID"]] = ad
            else:
                print(f"Invalid ad data for adID {adID}: {ad}")
        return jsonify(ads) 

@app.route('/getAd/<string:adID>', methods=['GET'])
@tracing.trace()
def getAd(adID):
    with tracer.start_active_span('/offer-banner/getAd/<adID>') as scope:

        with tracer.start_active_span('redis_get') as redis_span:
            trace_redis_operation(redis_span, 'get', adID)
            ad = redis_command(r_client.get, adID)

        if ad is None:
            return {}, 404
        else:
            try:
                return json.loads(ad.decode('utf-8'))
            except json.JSONDecodeError as e:
                print(f"JSONDecodeError: {e}")
                print(f"Raw ad data: {ad}")
                return {}

@app.route('/updateAd', methods=['POST'])
@tracing.trace()
def updateAd():
    with tracer.start_active_span('/offer-banner/updateAd') as scope:
        jsonData = request.json
        ad = Ad(**jsonData)

        with tracer.start_active_span('redis_set') as redis_span:
            trace_redis_operation(redis_span, 'set', ad.adID, json.dumps(ad.__dict__))
            redis_command(r_client.set, ad.adID, json.dumps(ad.__dict__))

        return "Success", 200

@app.route('/updateAds', methods=['POST'])
@tracing.trace()
def updateAds():
    with tracer.start_active_span('/offer-banner/updateAds') as scope:
        jsonData = request.json
        for ad_data in jsonData:
            ad = Ad(**ad_data)
            updateAd(ad)
        return "Success", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=SELF_PORT, debug=True)
