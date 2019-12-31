
# "Autobox" dongle driver for HTML 'streaming'
# Created by Colin Munro, December 2019
# See README.md for more information

"""Utility code to open a web server with 100 handler threads and respond to requests for static PNGs of the
    current frame, and send touches back. Includes the HTML to do so."""

import threading, socket
from queue import Queue
from functools import partial
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib
import simplejson

class Server:

	def __init__(self, port=9000, thread_pool=100):
		self.streams = []
		self.streamdata = []
		self.addr = ('', port)
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.sock.bind(self.addr)
		self.sock.listen(5)
		[self._Thread(self) for i in range(thread_pool)]

	def send_stream(self, data):
		self.streamdata.append(data)
		for x in self.streams:
			x.stream.put(data)

	class _Thread(threading.Thread):
		def __init__(self, owner):
			super().__init__()
			self.owner = owner
			self.daemon = True
			self.start()
		def run(self):
			httpd = HTTPServer(self.owner.addr, partial(self.owner._Handler, self.owner), False)
			httpd.socket = self.owner.sock
			httpd.server_bind = self.server_close = lambda self: None
			httpd.serve_forever()

	class _Handler(BaseHTTPRequestHandler):
		def __init__(self, owner, *args, **kwargs):
			self.owner = owner
			super().__init__(*args, **kwargs)
		
		def log_message(self, format, *args):
			pass

		def get_index(self):
			self.wfile.write("""
<html>
<head>
<title>TeslaCarPlay</title>
<style>
img {
position: absolute;
top: 50%;
left: 50%;
width: 800px;
height: 600px;
margin-top: -400px;
margin-left: -300px;
}
</style>
</head>
<body onload="run()" style="margin: 0px; background: #000000;">
<img id="display">
<script>
function mouse(type, event) {
	fetch("/touch", {method: 'POST', cache: 'no-cache', body: JSON.stringify({"type": type, "x": event.offsetX, "y": event.offsetY})})
	.then((response) => {
		return response.json();
	})
	.then((json) => {
		if (!json["ok"])
			console.log("Error sending touch");
	});
}
function loadimage(url, handle) {
    var downloading = new Image();
    downloading.onload = function(){
        handle(downloading);
    };
    downloading.onerror = function(){
        handle(null);
    };
    downloading.src = url;
}
var image = document.getElementById("display");
var count = 0;
function handle(img) {
    if (img !== null)
        image.src = img.src;
    loadimage("/snapshot?" + count.toString(), handle);
    count++;
}
function run() {
	image.draggable = false;
	var mousedown = false;
	image.onpointerdown = function(event){
		mouse("down", event);
		mousedown = true;
	};
	image.onpointermove = function(event){
		if (mousedown)
			mouse("move", event);
	};
	image.onpointerup = function(event){
		mousedown = false;
		mouse("up", event);
	};
    loadimage("/snapshot", handle);
}
</script>
</body>
</html>
""".encode('utf-8'))

		def get_stream(self):
			self.stream = Queue()
			temp_data = self.owner.streamdata
			i=0
			for x in temp_data:
				self.wfile.write(x)
				i+=len(x)
			print(f"<<preloaded {i} bytes>>")
			self.owner.streams.append(self)
			try:
				while True:
					chunk=self.stream.get(True, None)
					self.wfile.write(chunk)
					print(f"<<sent {len(chunk)} bytes>>")
				
			finally:
				self.owner.streams.remove(self)

		def get_ping(self):
			self.wfile.write(self.owner.on_get_snapshot())

		def do_touch(self, json):
			self.owner.on_touch(json["type"], json["x"], json["y"])
			self.wfile.write(simplejson.dumps({"ok": True}).encode('utf-8'))
	
		pages = {
			"/": ("text/html; charset=utf-8", get_index),
			"/stream": ("video/H264", get_stream),
			"/snapshot": ("image/png", get_ping),
		}

		posts = {
			"/touch": do_touch,
		}

		def do_GET(self):
			self.close_connection = True
			urldata = urllib.parse.urlparse(self.path)
			getter = self.pages.get(urldata.path, None)
			if getter is None:
				self.send_error(404, "Invalid path")
				return
			self.send_response(200)
			self.send_header("Content-type", getter[0])
			self.end_headers()
			try:
				getter[1](self)
			except (BrokenPipeError, ConnectionResetError):
				pass

		def do_POST(self):
			self.close_connection = True
			urldata = urllib.parse.urlparse(self.path)
			poster = self.posts.get(urldata.path, None)
			if poster is None:
				self.send_error(404, "Invalid path")
				return
			self.send_response(200)
			self.send_header("Content-type", "text/json")
			self.end_headers()
			content_len = int(self.headers.get('Content-length', 0))
			poster(self, simplejson.loads(self.rfile.read(content_len)))

	def on_touch(self, type, x, y):
		"""Callback for when a touch is received from the web browser [called from a web server thread]."""
		pass

	def on_get_snapshot(self):
		"""Callback for when a new PNG is required [called from a web server thread]."""
		return b''
