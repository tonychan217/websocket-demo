#!/usr/bin/python

# Python WebSocket Server for Raspberry Pi / PiFace
# by David Art [aka] adcomp <david.madbox@gmail.com>

import tornado.httpserver
import tornado.websocket
import tornado.ioloop
import tornado.web

import datetime
import json
import sys
import os

# PiFace module & init
import pifacedigitalio as pfio
pfio.init()
pifacedigital = pfio.PiFaceDigital()

class IndexHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        self.render("index.html")

class WebSocketHandler(tornado.websocket.WebSocketHandler):

  clients = []
  last_data = None

  def open(self):
    self.connected = True
    print("new connection")
    self.clients.append(self)
    self.timeout_loop()

  # """ Tornado 4.0 introduced an, on by default, same origin check.
  # This checks that the origin header set by the browser is the same as the host header """
  def check_origin(self, origin):
    return True

  def on_message(self, message):
    # message is the PIN number you want to toggle
    pin = int(message)
    # read output state
    r_output = '{0:08b}'.format(pifacedigital.output_port.value)
    # toggle output
    pin_state = int(r_output[7-pin]);
    pfio.digital_write(pin, not pin_state)
    # FIXME! I need to check with the loop so I don't send twice ?
    self.timeout_loop()

  def on_close(self):
    self.connected = False
    print("connection closed")
    self.clients.remove(self)

  def timeout_loop(self):
    # read PiFace input/output state
    r_input = '{0:08b}'.format(pifacedigital.input_port.value)
    r_output = '{0:08b}'.format(pifacedigital.output_port.value)

    # obj -> javascript
    data = {"in": [], "out": []}

    for i in range(8):
      data['in'].append(r_input[7-i])
      data['out'].append(r_output[7-i])

    # only send message if input/output changed
    if data != self.last_data:
      for client in self.clients:
        client.write_message(json.dumps(data))
    self.last_data = data

    # here come the magic part .. loop
    # FIXME! this is going pretty bad if too many clients I think ..
    # no other way to do this ?
    if self.connected:
      tornado.ioloop.IOLoop.instance().add_timeout(datetime.timedelta(seconds=.5), self.timeout_loop)

application = tornado.web.Application([
  (r'/', IndexHandler),
  (r'/piface', WebSocketHandler)
])

if __name__ == "__main__":
  http_server = tornado.httpserver.HTTPServer(application)
  http_server.listen(8888)
  print("Raspberry Pi - PiFace")
  print("WebSocket Server start ..")
  try:
    tornado.ioloop.IOLoop.instance().start()
  except KeyboardInterrupt:
    print('\nExit ..')
    sys.exit(0)
