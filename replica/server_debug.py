import os
import time
import redis
import requests
import subprocess

from flask import Flask, current_app

app = Flask(__name__)
app.init = False
# app.redis_conn = redis.StrictRedis("redis")
app.redis_conn = redis.StrictRedis(host='127.0.0.1', port=6379, db=0)
ENV = os.environ
ENV['REPLICA_NAME'] = 'replica_0'
ENV['QL_DEV'] = '/dev/ttyUSB3'
ENV['AT_DEV'] = '/dev/ttyUSB2'
INIT = False


def is_run():
    try:
        result = subprocess.check_output("ifconfig | grep ppp0", stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError:
        result = None
    if result:
        return True
    return False


@app.route("/connect")
def connect(isFirstRun=False):
    while 1:
        if is_run() is False:
            subprocess.run("sh /home/quectel-pppd.sh", shell=True)
        else:
            break
        time.sleep(3)
    subprocess.run("tinyproxy", shell=True)
    if isFirstRun == False:
        current_app.redis_conn.set(ENV["REPLICA_NAME"], 1)
    requests.get("http://127.0.0.1:5000/refresh_squid")
    return "done."


@app.route("/disconnect")
def disconnect():
    current_app.redis_conn.set(ENV["REPLICA_NAME"], 0)
    if is_run():
        subprocess.run("killall tinyproxy", shell=True)
        subprocess.run("sh /home/quectel-ppp-kill.sh", shell=True)
        requests.get("http://127.0.0.1:5000/refresh_squid")
        subprocess.run(f'echo -e -n "AT+CFUN=0\x0D\x0A" > {ENV["AT_DEV"]}', shell=True)
        time.sleep(0.5)
        subprocess.run(f'echo -e -n "AT+CFUN=1\x0D\x0A" > {ENV["AT_DEV"]}', shell=True)
        time.sleep(3)
    return "done."


@app.route("/reconnect")
def reconnect():
    if is_run():
        disconnect()
        time.sleep(1)
        connect()
    else:
        connect()
    return "done."


@app.route("/status")
def get_status():
    return str(is_run())


if __name__ == '__main__':
    app.redis_conn.hset("replicas", ENV["REPLICA_NAME"], 1)
    connect(isFirstRun=True)
    app.run(host="0.0.0.0", port=5001)
