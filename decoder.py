
# "Autobox" dongle driver for HTML 'streaming'
# Created by Colin Munro, December 2019
# See README.md for more information

"""Simple utility code to decode an h264 stream to a series of PNGs."""

import subprocess, threading, os, fcntl

class Decoder:
	class _Thread(threading.Thread):
		def __init__(self, owner):
			super().__init__()
			self.owner = owner
			self.running = threading.Event()
			self.shutdown = False

		def run(self):
			png_header = bytearray([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
			captured_data = b''
			checked = 0
			while not self.shutdown:
				data = self.owner.child.stdout.read(1024000)
				if data is None or not len(data):
					self.running.clear()
					self.running.wait(timeout=0.1)
					continue
				captured_data += data
				first_header = captured_data.find(png_header)
				if first_header == -1:
					continue
				if first_header != 0:
					captured_data = captured_data[first_header:]
				while True:
					second_header = captured_data.find(png_header, checked)
					if second_header == -1:
						checked = len(captured_data) - len(png_header)
						break
					png = captured_data[:second_header]
					captured_data = captured_data[second_header:]
					checked = len(png_header)
					self.owner.on_frame(png)

	def __init__(self):
		self.child = subprocess.Popen(["ffmpeg", "-threads", "4", "-i", "-", "-vf", "fps=7", "-c:v", "png", "-f", "image2pipe", "-"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=1)
		fd = self.child.stdout.fileno()
		fl = fcntl.fcntl(fd, fcntl.F_GETFL)
		fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
		self.thread = self._Thread(self)
		self.thread.start()

	def stop(self):
		self.child.terminate()
		self.thread.shutdown = True
		self.thread.join()

	def send(self, data):
		self.child.stdin.write(data)
		self.child.stdin.flush()
		self.thread.running.set()

	def on_frame(self, png):
		"""Callback for when a frame is received [called from a worker thread]."""
		pass
