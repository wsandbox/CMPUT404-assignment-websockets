#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2013-2014 Abram Hindle
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import json
import os
import time

import flask
import gevent
from flask import Flask, request
from flask_sockets import Sockets
from gevent import queue

app = Flask(__name__)
sockets = Sockets(app)
app.debug = True

clients = list()

class Client:
    def __init__(self):
        self.queue = queue.Queue()

    def put(self, v):
        self.queue.put_nowait(v)

    def get(self):
        return self.queue.get()

class World:
    def __init__(self):
        self.listeners = list()
        self.clear()
        
    def add_set_listener(self, listener):
        self.listeners.append( listener )

    def update(self, entity, key, value):
        entry = self.space.get(entity,dict())
        entry[key] = value
        self.space[entity] = entry
        self.update_listeners( entity )

    def set(self, entity, data):
        self.space[entity] = data
        self.update_listeners( entity )

    def update_listeners(self, entity):
        for listener in self.listeners:
            listener(entity, self.get(entity))
            
    def clear(self):
        self.space = dict()
        self.update_listeners(self.world())

    def get(self, entity):
        return self.space.get(entity,dict())
    
    def world(self):
        return self.space

myWorld = World()        

def set_listener( entity, data ):
    packet = json.dumps({entity:data})
    for client in clients:
        # print('set_listener')
        client.put(packet)

myWorld.add_set_listener( set_listener )
        
@app.route('/')
def hello():
    return flask.redirect('static/index.html')

def read_ws(ws,client):
    try:
        while True:
            msg = ws.receive()
            # print("WS RECV: %s" % msg)
            if (msg is not None):
                data = json.loads(msg)
                for entity in data:
                    myWorld.set(entity,data[entity])
            else:
                break
    except Exception as e:
        print("READ_WS ERROR:",e)
    return None

@sockets.route('/subscribe')
def subscribe_socket(ws):
    client = Client()
    clients.append(client)
    q = gevent.spawn(read_ws, ws, client)
    try:
        data = json.dumps(myWorld.world())
        ws.send(data)
        while True:
            msg = client.get()
            # print('subscribed',msg)
            ws.send(msg)
    except Exception as e:
        print("SUBSCRIBE ERROR:",e)
    finally:
        clients.remove(client)
        gevent.kill(q)

def flask_post_json():
    if (request.json != None):
        return request.json
    elif (request.data != None and request.data.decode("utf8") != u''):
        return json.loads(request.data.decode("utf8"))
    else:
        return json.loads(request.form.keys()[0])

@app.route("/entity/<entity>", methods=['POST','PUT'])
def update(entity):
    '''update the entities via this interface'''
    data = flask_post_json()
    for key, value in data.items():
        myWorld.update(entity, key, value)
        myWorld.update_listeners(entity)
    return flask.jsonify(myWorld.get(entity))

@app.route("/world", methods=['POST','GET'])    
def world():
    return flask.jsonify(myWorld.world())

@app.route("/entity/<entity>")    
def get_entity(entity):
    return flask.jsonify(myWorld.get(entity))


@app.route("/clear", methods=['POST','GET'])
def clear():
    myWorld.clear()
    return flask.jsonify(myWorld.world())


if __name__ == "__main__":
    app.run()