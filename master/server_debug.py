import asyncio
import traceback

import aiofiles
import aiohttp
import aredis
import redis
from quart import Quart, request, current_app, jsonify

app = Quart(__name__)
# app.redis_conn = aredis.StrictRedis("redis")
app.redis_conn = redis.StrictRedis(host='127.0.0.1', port=6379, db=0)


def get_replicas(run_type):
    replicas_ = [replica.decode() for replica in (app.redis_conn.hgetall("replicas")).keys()]
    result = []
    if run_type == 2:
        return replicas_
    for replica in replicas_:
        replica_status = current_app.redis_conn.get(replica)
        if replica_status is None:
            replica_status = 0
        if int(replica_status) == run_type:
            result.append(replica)
    return result


@app.route("/replicas")
def replicas():
    return jsonify(get_replicas(int(request.args.get("type", "1"))))


@app.route("/refresh_ip/<replica_num>")
async def refresh_ip(replica_num):
    try:
        async with aiohttp.ClientSession() as session:
            await session.get(f"http://replica_{replica_num}:5000/reconnect")
        return ""
    except:
        return "error"


@app.route("/refresh_squid")
def refresh_squid_api():
    refresh_squid()
    return ""


def refresh_squid():
    while 1:
        try:
            replicas_ = get_replicas(run_type=1)
            _ = [f"cache_peer {replica} parent 3128 0 no-query\n" for replica in replicas_]
            with open("/home/squid.conf.example", "r") as example_file:
                with open("/etc/squid/squid.conf", "w") as output_file:
                    conf = example_file.read()
                    output_file.write(conf + f"\n\n{''.join(_)}")
            import subprocess
            subprocess.run("squid -k reconfigure", shell=True)
            break
        except:
            app.logger.error(traceback.format_exc())
            # asyncio.sleep(1)


if __name__ == '__main__':
    app.run("0.0.0.0")
