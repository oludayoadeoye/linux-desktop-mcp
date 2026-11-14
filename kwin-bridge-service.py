#!/usr/bin/python
"""Session D-Bus bridge used by the KWin JavaScript integration."""

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

BUS = "org.chatgpt.DesktopControl"
OBJECT_PATH = "/org/chatgpt/DesktopControl"
INTERFACE = "org.chatgpt.DesktopControl"


class DesktopControl(dbus.service.Object):
    def __init__(self, bus):
        super().__init__(bus, OBJECT_PATH)
        self.windows = "[]"
        self.command = "{}"
        self.log = ""

    @dbus.service.method(INTERFACE, in_signature="s", out_signature="")
    def UpdateWindows(self, payload):
        self.windows = payload

    @dbus.service.method(INTERFACE, in_signature="", out_signature="s")
    def GetWindows(self):
        return self.windows

    @dbus.service.method(INTERFACE, in_signature="s", out_signature="")
    def SetCommand(self, payload):
        self.command = payload

    @dbus.service.method(INTERFACE, in_signature="", out_signature="s")
    def GetCommand(self):
        value = self.command
        self.command = "{}"
        return value

    @dbus.service.method(INTERFACE, in_signature="s", out_signature="")
    def Log(self, payload):
        self.log = payload

    @dbus.service.method(INTERFACE, in_signature="", out_signature="s")
    def GetLog(self):
        return self.log


if __name__ == "__main__":
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()
    name = dbus.service.BusName(BUS, bus=bus, do_not_queue=True)
    obj = DesktopControl(bus)
    print("Desktop Control KWin bridge ready", flush=True)
    GLib.MainLoop().run()
