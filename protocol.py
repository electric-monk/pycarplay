
# "Autobox" dongle driver for HTML 'streaming'
# Created by Colin Munro, December 2019
# See README.md for more information

"""Dongle communications protocol implementation."""

import struct
from enum import IntEnum

def _setenum(enum, val):
    try:
        return enum(val)
    except ValueError:
        return val

class Message:
    """Base dongle message, indicating message size and type."""
    magic = 0x55aa55aa
    headersize = 4 * 4
    
    @classmethod
    def _allmessages(cls):
        """Get a dictionary mapping message types to messages."""
        msgs = {}
        for x in cls.__subclasses__():
            if hasattr(x, 'msgtype'):
                msgs[x.msgtype] = x
            msgs.update(x._allmessages())
        return msgs
    
    def upgrade(self, bodydata):
        """Convert a message containing only its header to the concrete message type (if known)."""
        try:
            upd=self._allmessages()[self.type]()
            upd._setdata(bodydata)
            upd._check_type()
        except KeyError:
            upd=Unknown(self.type)
            upd._setdata(bodydata)
        except struct.error:
            upd=Unknown(self.type)
            upd._setdata(bodydata)    
        return upd
    
    def __init__(self, type=-1):
        if type == -1 and hasattr(self, "msgtype"):
            self.type = self.msgtype
        else:
            self.type = type
    
    def serialise(self):
        data = self._data()
        return struct.pack("<LLLL", self.magic, len(data), self.type, (self.type ^ -1) & 0xffffffff) + data
    
    def deserialise(self, data):
        (magic, datalen, self.type, typecheck) = struct.unpack("<LLLL", data[:16])
        if typecheck != (self.type ^ -1) & 0xffffffff:
            raise ValueError("Message failed check")
        if magic != self.magic:
            raise ValueError("Magic number incorrect")
        rest = data[16:]
        if len(rest) == datalen:
            self._setdata(rest[:datalen])
        else:
            self._setdata(b'\0' * datalen)
        self._check_type()
        
    def _check_type(self):
        if hasattr(self, "msgtype"):
            if self.type != self.msgtype:
                raise ValueError("Type mis-restored")

    def _data(self):
        return self._default_data
    
    def _setdata(self, data):
        self._default_data = data

class Unknown(Message):
    pass

class SendFile(Message):
    msgtype = 153
    
    def __init__(self, filename = "", content = b""):
        super().__init__(self.msgtype)
        self.filename = filename
        self.content = content
    
    def _data(self):
        actualfilename = (self.filename + '\0').encode('ascii')
        return struct.pack("<L", len(actualfilename)) + actualfilename + struct.pack("<L", len(self.content)) + self.content
    
    def _setdata(self, data):
        (length,) = struct.unpack("<L", data[:4])
        self.filename = data[4:][:length - 1].decode('ascii')
        second = data[4 + length:]
        (length,) = struct.unpack("<L", second[:4])
        self.content = second[4:][:length]

class Open(Message):
    msgtype = 1
    
    def __init__(self):
        super().__init__(self.msgtype)
        # Some default values to use
        self.width = 800
        self.height = 600
        self.videoFrameRate = 60
        self.format = 5
        self.packetMax = 49152
        self.iBoxVersion = 2
        self.phoneWorkMode = 2
    
    def _data(self):
        return struct.pack("<LLLLLLL", self.width, self.height, self.videoFrameRate, self.format, self.packetMax, self.iBoxVersion, self.phoneWorkMode)
    
    def _setdata(self, data):
        (self.width, self.height, self.videoFrameRate, self.format, self.packetMax, self.iBoxVersion, self.phoneWorkMode) = struct.unpack("<LLLLLLL", data)

class Heartbeat(Message):
    msgtype = 170
    lifecycle = 2 # seconds
    
    def __init__(self):
        super().__init__(self.msgtype)
    
    def _data(self):
        return b""
    
    def _setdata(self, data):
        if len(data):
            raise ValueError("Heartbeat message should not contain data")

class ManufacturerInfo(Message):
    msgtype = 20
    
    def __init__(self, a = -1, b = -1):
        super().__init__(self.msgtype)
        self.a = a
        self.b = b
    
    def _data(self):
        return struct.pack("<LL", self.a, self.b)
    
    def _setdata(self,data):
        (self.a, self.b) = struct.unpack("<LL", data)

class CarPlay(Message):
    msgtype = 8
    
    class Value(IntEnum):
        Invalid = 0
        BtnSiri = 5
        CarMicrophone = 7
        BtnLeft = 100
        BtnRight = 101
        BtnSelectDown = 104
        BtnSelectUp = 105 
        BtnBack = 106
        BtnDown = 114
        BtnHome = 200
        BtnPlay = 201
        BtnPause = 202
        BtnNextTrack = 204
        BtnPrevTrack = 205
        SupportWifi = 1000
        SupportWifiNeedKo = 1012
    
    def __init__(self, v = 0):
        super().__init__(self.msgtype)
        self.value = _setenum(self.Value, v)

    def _data(self):
        return struct.pack("<L", self.value)
    
    def _setdata(self, data):
        (v,) = struct.unpack("<L", data)
        self.value = _setenum(self.Value, v)

class SoftwareVersion(Message):
    msgtype = 204
    
    def __init__(self, swv = ""):
        super().__init__(self.msgtype)
        self.version = swv
    
    def _data(self):
        s = self.version.encode('ascii')
        return s + b'\0' * (32 - len(s))
    
    def _setdata(self, data):
        self.version = bytearray(data).decode('ascii').rstrip('\x00')

class BluetoothAddress(Message):
    msgtype = 10
    
    def __init__(self):
        super().__init__(self.msgtype)
        self.address = "1f:ea:27:37:d6:51" # randomly generated, just for testing
    
    def _data(self):
        return self.address.encode('ascii')
    
    def _setdata(self, data):
        self.address = bytearray(data).decode('ascii')
        if len(self.address) != 17:
            raise "wrong length data"

class BluetoothPIN(Message):
    msgtype = 12
    
    def __init__(self):
        super().__init__(self.msgtype)
        self.pin = "1234"
    
    def _data(self):
        return self.pin.encode('ascii')
    
    def _setdata(self, data):
        self.pin = bytearray(data).decode('ascii')
        if len(self.pin) != 4:
            raise ValueError("Wrong length data")

class Plugged(Message):
    msgtype = 2
    
    def __init__(self, wifistyle = False):
        super().__init__(self.msgtype)
        self.wifistyle = wifistyle
        self.phone_type = 0
        self.wifi = False
    
    def _data(self):
        if self.wifistyle:
            return struct.pack("<LL", self.phone_type, 1 if self.wifi else 0)
        else:
            return struct.pack("<L", self.phone_type)

    def _setdata(self, data):
        self.wifistyle = len(data) == 8
        if self.wifistyle:
            (self.phone_type, self.wifi) = struct.unpack("<LL", data)
        else:
            (self.phone_type,) = struct.unpack("<L", data)

class Unplugged(Message):
    msgtype = 4

class VideoData(Message):
    msgtype = 6
    
    def __init__(self):
        super().__init__(self.msgtype)
    
    def _setdata(self, data):
        (self.width, self.height, self.flags, self.unknown1, self.unknown2) = struct.unpack("<LLLLL", data[:20])
        # at least for format==5, self.data is h264
        self.data = data[20:]

class AudioData(Message):
    msgtype = 7
    
    class Command(IntEnum):
        AUDIO_OUTPUT_START = 1
        AUDIO_OUTPUT_STOP = 2
        AUDIO_INPUT_CONFIG = 3
        AUDIO_PHONECALL_START = 4
        AUDIO_PHONECALL_STOP = 5
        AUDIO_NAVI_START = 6
        AUDIO_NAVI_STOP = 7
        AUDIO_SIRI_START = 8
        AUDIO_SIRI_STOP = 9
        AUDIO_MEDIA_START = 0xA
        AUDIO_MEDIA_STOP = 0xB
    
    @staticmethod
    def _format_for_decodetype(x):
        one = (44100, 2, 16)
        options = {
            1: one,
            2: one,
            3: (8000, 1, 16),
            4: (48000, 2, 16),
            5: (16000, 1, 16),
            6: (24000, 1, 16),
            7: (16000, 2, 16),
        }
        return options.get(x, (0, 0, 0))
    
    def __init__(self):
        super().__init__(self.msgtype)
    
    def _setdata(self, data):
        amount = len(data) - 12
        (self.decodeType, self.volume, self.audioType) = struct.unpack("<LfL", data[:12])
        if amount == 1:
            self.command = _setenum(self.Command, data[12])
        elif amount == 4:
            self.volumeDuration = struct.unpack("<L", data[12:])
        else:
            # data is uncompressed, of the format specified in self.decodeType (ints appear to be signed)
            self.data = data[12:]

# X/Y are scaled from 0 to 10000 regardless of device resolution
class Touch(Message):
    msgtype = 5
    
    class Action(IntEnum):
        Down = 14
        Move = 15
        Up = 16
    
    def __init__(self):
        super().__init__(self.msgtype)
        self.x = 0
        self.y = 0
        self.action = self.Action.Up
    
    def _data(self):
        return struct.pack("<LLLL", self.action.value, self.x, self.y, 0)
    
    def _setdata(self, data):
        (action, self.x, self.y, self.flags) = struct.unpack("<LLLL", data)
        self.action = _setenum(self.Action, action)

class MultiTouch(Message):
    msgtype = 23
    
    class Touch:
        class Action(IntEnum):
            Down = 1
            Move = 2
            Up = 0
        
        def __init__(self):
            self.x = 0
            self.y = 0
            self.action = self.Action.Up
            self.id = 4
        
        def serialise(self):
            return struct.pack("<ffLL", self.x, self.y, self.action.value, self.id)
    
    def __init__(self):
        super().__init__(self.msgtype)
        self.touches = []
    
    def _data(self):
        return b''.join([x.serialise() for x in self.touches])

def _send_string(filename, s):
    if len(s) > 16:
        raise "String too long"
    return SendFile(filename, s.encode('ascii'))

def _send_int(filename, i):
    return SendFile(filename, struct.pack("<L", i))

def _copy_assets(ar):
    def get(filename):
        with open(filename, "rb") as f:
            return f.read()
    return [SendFile(f"/tmp/{x}", get(f"assets/{x}")) for x in ar]

# These files were included in the original APK, and are easily extracted. They're kind of interesting and probably warrant investigation.
_assets = ["adb", "adb.pub", "helloworld0", "helloworld1", "helloworld2", "libby265n.so", "libby265n_x86.so", "libscreencap40.so", "libscreencap41.so", "libscreencap43.so", "libscreencap50.so", "libscreencap50_x86.so", "libscreencap442.so", "libscreencap422.so", "mirrorcoper.apk", "libscreencap60.so", "libscreencap70.so", "libscreencap71.so", "libscreencap80.so", "libscreencap90.so", "HWTouch.dex"]

opened_info = [
   ManufacturerInfo(0, 0),
   _send_int("/tmp/night_mode", 0),    # 0==day, 1==night
   _send_int("/tmp/hand_drive_mode", 0),    # 0==left, 1==right
   _send_int("/tmp/charge_mode", 0),
   _send_string("/etc/box_name", "Teslabox"),
]

startup_info = [
    _send_int("/tmp/screen_dpi", 160),
] + _copy_assets(_assets) + [
    Open(),
]
