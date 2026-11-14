function sendWindowList() {
    var rows = workspace.windowList().map(function(w, index) {
        return {index:index,caption:String(w.caption||""),resourceClass:String(w.resourceClass||""),
            resourceName:String(w.resourceName||""),pid:Number(w.pid||0),minimized:Boolean(w.minimized),
            active:Boolean(w.active),desktop:Number(w.desktop||0),maximized:Boolean(w.maximized),
            uuid:String(w.internalId||"")};
    });
    callDBus("org.chatgpt.DesktopControl","/org/chatgpt/DesktopControl",
        "org.chatgpt.DesktopControl","UpdateWindows",JSON.stringify(rows));
}
function executeDesktopCommand() {
    callDBus("org.chatgpt.DesktopControl","/org/chatgpt/DesktopControl",
        "org.chatgpt.DesktopControl","GetCommand",function(payload) {
            var command;
            try { command=JSON.parse(payload); } catch(e) { return; }
            if (!command || !command.action) return;
            var windows=workspace.windowList(), target=null, match=String(command.match||"").toLowerCase();
            for (var i=0;i<windows.length;i++) {
                var w=windows[i];
                if ((command.pid && Number(w.pid)===Number(command.pid)) ||
                    (match && (String(w.resourceClass).toLowerCase()===match ||
                               String(w.resourceName).toLowerCase()===match))) {
                    target=w; break;
                }
            }
            if (!target && match) {
                for (var j=0;j<windows.length;j++) {
                    if (String(windows[j].caption||"").toLowerCase().indexOf(match)>=0) {
                        target=windows[j]; break;
                    }
                }
            }
            if (!target) return;
            if (command.action==="focus") {
                target.minimized=false; workspace.activeWindow=target;
            } else if (command.action==="minimize") {
                target.minimized=true;
            } else if (command.action==="maximize" || command.action==="restore") {
                target.minimized=false; workspace.activeWindow=target;
            } else if (command.action==="close") {
                target.closeWindow();
            }
            sendWindowList();
        });
}
registerShortcut("DesktopControlRefreshV5","Refresh desktop window list","Meta+Shift+F12",sendWindowList);
registerShortcut("DesktopControlCommandV5","Execute desktop control command","Meta+Shift+F11",executeDesktopCommand);
sendWindowList();
