const { contextBridge, ipcRenderer } = require("electron");
contextBridge.exposeInMainWorld("company", {
  request: (method, path, body) =>
    ipcRenderer.invoke("api", { method, path, body }),
  upload: () => ipcRenderer.invoke("upload"),
  download: (name) => ipcRenderer.invoke("download", name),
  invoice: (id) => ipcRenderer.invoke("invoice", id),
  export: (kind, format) => ipcRenderer.invoke("export", { kind, format }),
});
