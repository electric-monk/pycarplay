Python Carplay library for the "Autobox" dongles

# Dongles

These are readily available from Amazon, but are also available from cheaper sources. The one I got was labelled "Carlinkit" here: https://www.aliexpress.com/item/32829019768.html

They're provided with an Android APK (and if you hunt around online, a Windows CE version of the 'player' application also exists).

## Interesting observations

* During boot, a bunch of files are copied to the dongle, with a target path beginning with `/tmp/` and occasionally `/etc/`. This implies the dongle itself is running something like Linux.
* Some files are also written to change settings, such as night mode, left or right hand drive, and "charge mode" for the USB port.
* There may be multiple versions, possibly including whether or not the dongle supports wireless CarPlay, but I haven't investigated. I suspect the one I have doesn't support wireless CarPlay because there's a point at which the dongle can indicate support, optionally requesting a driver is uploaded, and mine never sends the message.

# Setup

The code provided was based on findings from the APK. As such, some functionality is duplicated that may not be necessary. The primary case is the copying of various "assets" to the dongle that happens on every boot. To acquire these assets, a script is provided.

Simply run:
```
./downloadassets.sh
```
from the repository root.

This script simply uses the URL that was printed on the front of the box my dongle came in.

## Python environment

The code is intended for Python3. To install the necessary packages, run this command:
```
pip3 install pyusb simplejson
```

# Implementation

Though I thought it'd be fun to have CarPlay on a Tesla, I was really interested in the dongle itself.

They're pretty mysterious, providing CarPlay and Android Auto functionality in a way that clearly wasn't intended by Apple or Google. Further investigation indicates they may come from a line of products that can also support AirPlay and other streaming without needing an Apple-specific dongle.

## Structure

The program is split into a few files:

* decoder.py
   * convenience wrapper for a subprocess running `ffmpeg`, to take the received h264 and generate PNGs
* server.py
   * convenience wrapper for `http.server`, to server a basic "CarPlay" PNG-based webpage and get the touches out
* link.py
   * the USB-specific code, wrapping `pyusb` and the dongle's default interface with a reader thread (which parses messages) and a writer thread (with locking, as each module runs in its own thread)
* protocol.py
   * implemention of various messages the dongle sends and/or receives
* teslabox.py
   * test code to make the CarPlay webpage appear in a Tesla

## Issues

1. I only implemented the basic messages required to get things to work.
   * There's messages coming in that I can probably decode but didn't as they're not required right now. This includes a bunch of stuff relating to which microphone to use.
   * Android Auto hasn't been tested, nor has iOS 13 (though I imagine compatibility issues would be a dongle issue firstly). There's some evidence that Android Auto will behave quite differently with a bunch of different messages.
2. `ffmpeg` is communicated with via pipes.
   * This means if you don't read the `stdout` pipe fast enough, it blocks even if it has plenty of input data.
   * This could be solved with a native `ffmpeg` wrapper for python, or by just rewriting this all in C++.
3. It maxes out a Raspberry Pi model B, even with `ffmpeg` dropping frames intentionally.
4. Tesla-specific:
   * The Tesla web browser won't open private IPs. It may be possible to have a Raspberry Pi act as an AP and provide the interface on a "public" IP that it internally serves, then serve the rest of the internet normally, but I haven't tried this.
5. Doesn't seem to work on MacOS X (High Sierra)
   * I assume it's a libusb issue.
   
# Finally...

All work here was done simply as a research project, and largely for fun. I hope it can be of use to others who are interested!

Copyright (C) 2019 Colin Munro
