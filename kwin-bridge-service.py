#!/usr/bin/python
import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib
BUS="org.chatgpt.DesktopControl"; PATH="/org/chatgpt/DesktopControl"; IFACE="org.chatgpt.DesktopControl"
class DesktopControl(dbus.service.Object):
 def __init__(self,bus):
  super().__init__(bus,PATH); self.windows="[]"; self.command="{}"; self.log=""
 @dbus.service.method(IFACE,in_signature="s",out_signature="")
 def UpdateWindows(self,payload): self.windows=payload
 @dbus.service.method(IFACE,in_signature="",out_signature="s")
 def GetWindows(self): return self.windows
 @dbus.service.method(IFACE,in_signature="s",out_signature="")
 def SetCommand(self,payload): self.command=payload
 @dbus.service.method(IFACE,in_signature="",out_signature="s")
 def GetCommand(self):
  value=self.command; self.command="{}"; return value
 @dbus.service.method(IFACE,in_signature="s",out_signature="")
 def Log(self,payload): self.log=payload
 @dbus.service.method(IFACE,in_signature="",out_signature="s")
 def GetLog(self): return self.log
DBusGMainLoop(set_as_default=True); bus=dbus.SessionBus(); name=dbus.service.BusName(BUS,bus=bus,do_not_queue=True)
obj=DesktopControl(bus); print("Desktop Control KWin bridge ready",flush=True); GLib.MainLoop().run()
