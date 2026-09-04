(function () {
  var body = document.body;
  var folder = body.getAttribute("data-folder") || "";
  var dropZone = document.getElementById("dropZone");
  var fileInput = document.getElementById("fileInput");
  var openInOsBtn = document.getElementById("openInOsBtn");
  var progressContainer = document.getElementById("progressContainer");
  var progressBar = document.getElementById("progressBar");
  var progressPct = document.getElementById("progressPct");
  var progressSpeed = document.getElementById("progressSpeed");
  var progressEta = document.getElementById("progressEta");
  var statusText = document.getElementById("statusText");

  if (!folder) return;

  function formatBytes(bytes) {
    if (!bytes || bytes < 0) return "0 B";
    var units = ["B", "KB", "MB", "GB"];
    var i = 0;
    var n = bytes;
    while (n >= 1024 && i < units.length - 1) {
      n /= 1024;
      i += 1;
    }
    return (i === 0 ? Math.round(n) : n.toFixed(n >= 10 ? 1 : 2)) + " " + units[i];
  }

  function formatEta(seconds) {
    if (!isFinite(seconds) || seconds < 0) return "—";
    if (seconds < 1) return "<1s";
    if (seconds < 60) return Math.round(seconds) + "s";
    var m = Math.floor(seconds / 60);
    var s = Math.round(seconds % 60);
    return m + "m " + s + "s";
  }

  function setMeter(pct, speedText, etaText, bytesText) {
    if (progressPct) progressPct.textContent = pct;
    if (progressSpeed) progressSpeed.textContent = speedText;
    if (progressEta) progressEta.textContent = "ETA " + etaText;
    if (statusText && bytesText != null) statusText.textContent = bytesText;
  }

  function apiJson(url, payload) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then(function (res) {
      return res.json().then(function (data) {
        if (!res.ok) {
          var err = new Error((data && data.error) || "Falha na operação");
          err.status = res.status;
          throw err;
        }
        return data;
      });
    });
  }

  function reloadSoon() {
    setTimeout(function () {
      window.location.reload();
    }, 400);
  }

  if (openInOsBtn) {
    openInOsBtn.addEventListener("click", function () {
      fetch("/api/host/open?folder=" + encodeURIComponent(folder))
        .then(function (res) {
          return res.json().then(function (data) {
            if (!res.ok) throw new Error((data && data.error) || "Não foi possível abrir");
          });
        })
        .catch(function (err) {
          window.alert(err.message || "Não foi possível abrir a pasta.");
        });
    });
  }

  function enterRename(row) {
    var nameEl = row.querySelector(".file-name");
    var input = row.querySelector(".file-rename-input");
    if (!nameEl || !input) return;
    row.classList.add("is-renaming");
    nameEl.classList.add("hidden");
    input.classList.remove("hidden");
    input.value = row.getAttribute("data-filename") || "";
    row.querySelectorAll("[data-action='rename'], [data-action='delete']").forEach(function (btn) {
      btn.classList.add("hidden");
    });
    row.querySelectorAll("[data-action='save-rename'], [data-action='cancel-rename']").forEach(function (btn) {
      btn.classList.remove("hidden");
    });
    input.focus();
    input.select();
  }

  function exitRename(row) {
    var nameEl = row.querySelector(".file-name");
    var input = row.querySelector(".file-rename-input");
    if (!nameEl || !input) return;
    row.classList.remove("is-renaming");
    input.classList.add("hidden");
    nameEl.classList.remove("hidden");
    row.querySelectorAll("[data-action='rename'], [data-action='delete']").forEach(function (btn) {
      btn.classList.remove("hidden");
    });
    row.querySelectorAll("[data-action='save-rename'], [data-action='cancel-rename']").forEach(function (btn) {
      btn.classList.add("hidden");
    });
  }

  function saveRename(row) {
    var oldName = row.getAttribute("data-filename") || "";
    var input = row.querySelector(".file-rename-input");
    var newName = (input && input.value ? input.value : "").trim();
    if (!newName || newName === oldName) {
      exitRename(row);
      return;
    }
    apiJson("/api/host/rename", { folder: folder, name: oldName, new_name: newName })
      .then(function () {
        reloadSoon();
      })
      .catch(function (err) {
        window.alert(err.message || "Não foi possível renomear.");
        exitRename(row);
      });
  }

  function deleteFile(row) {
    var name = row.getAttribute("data-filename") || "";
    if (!name) return;
    if (!window.confirm('Apagar "' + name + '"?')) return;
    apiJson("/api/host/delete", { folder: folder, name: name })
      .then(function () {
        reloadSoon();
      })
      .catch(function (err) {
        window.alert(err.message || "Não foi possível apagar.");
      });
  }

  var fileListEl = document.getElementById("fileList");
  if (fileListEl) {
    fileListEl.addEventListener("click", function (e) {
      var btn = e.target.closest("[data-action]");
      if (!btn) return;
      var row = btn.closest(".file-row");
      if (!row) return;
      var action = btn.getAttribute("data-action");
      if (action === "rename") enterRename(row);
      else if (action === "cancel-rename") exitRename(row);
      else if (action === "save-rename") saveRename(row);
      else if (action === "delete") deleteFile(row);
    });

    fileListEl.addEventListener("keydown", function (e) {
      var input = e.target.closest(".file-rename-input");
      if (!input) return;
      var row = input.closest(".file-row");
      if (!row) return;
      if (e.key === "Enter") {
        e.preventDefault();
        saveRename(row);
      } else if (e.key === "Escape") {
        e.preventDefault();
        exitRename(row);
      }
    });
  }

  function uploadFiles(fileList) {
    if (!fileList || !fileList.length) return;
    var formData = new FormData();
    for (var i = 0; i < fileList.length; i++) {
      formData.append("file", fileList[i]);
    }
    formData.append("folder", folder);

    var xhr = new XMLHttpRequest();
    var startedAt = Date.now();
    var lastLoaded = 0;
    var lastAt = startedAt;

    if (progressContainer) progressContainer.classList.remove("hidden");
    if (statusText) {
      statusText.classList.remove("text-success", "text-danger");
    }
    setMeter("0%", "—", "—", "Iniciando…");
    if (progressBar) progressBar.style.width = "0%";
    if (dropZone) dropZone.classList.add("is-busy");

    xhr.upload.onprogress = function (ev) {
      if (!ev.lengthComputable) return;
      var now = Date.now();
      var percent = (ev.loaded / ev.total) * 100;
      if (progressBar) progressBar.style.width = percent + "%";
      var dt = (now - lastAt) / 1000;
      var speed = dt > 0 ? (ev.loaded - lastLoaded) / dt : 0;
      if (dt >= 0.25) {
        lastLoaded = ev.loaded;
        lastAt = now;
      }
      var elapsed = (now - startedAt) / 1000;
      var avgSpeed = elapsed > 0 ? ev.loaded / elapsed : 0;
      var remaining = avgSpeed > 0 ? (ev.total - ev.loaded) / avgSpeed : NaN;
      var showSpeed = speed > 0 ? speed : avgSpeed;
      setMeter(
        Math.round(percent) + "%",
        formatBytes(showSpeed) + "/s",
        formatEta(remaining),
        formatBytes(ev.loaded) + " de " + formatBytes(ev.total)
      );
    };

    xhr.onload = function () {
      if (dropZone) dropZone.classList.remove("is-busy");
      var ok = xhr.status === 200;
      try {
        var data = JSON.parse(xhr.responseText || "{}");
        if (!ok) throw new Error(data.error || "Erro ao enviar");
      } catch (err) {
        if (statusText) {
          statusText.textContent = err.message || "Erro ao enviar.";
          statusText.classList.add("text-danger");
        }
        return;
      }
      if (progressBar) progressBar.style.width = "100%";
      setMeter("100%", "concluído", "0s", "Arquivos adicionados");
      if (statusText) statusText.classList.add("text-success");
      reloadSoon();
    };

    xhr.onerror = function () {
      if (dropZone) dropZone.classList.remove("is-busy");
      if (statusText) {
        statusText.textContent = "Erro de rede ao enviar.";
        statusText.classList.add("text-danger");
      }
    };

    xhr.open("POST", "/api/host/upload", true);
    xhr.send(formData);
  }

  if (fileInput) {
    fileInput.addEventListener("change", function () {
      uploadFiles(fileInput.files);
      fileInput.value = "";
    });
  }

  if (dropZone) {
    ["dragenter", "dragover"].forEach(function (eventName) {
      dropZone.addEventListener(eventName, function (e) {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.add("is-dragover");
      });
    });
    ["dragleave", "drop"].forEach(function (eventName) {
      dropZone.addEventListener(eventName, function (e) {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove("is-dragover");
      });
    });
    dropZone.addEventListener("drop", function (e) {
      if (e.dataTransfer && e.dataTransfer.files.length) {
        uploadFiles(e.dataTransfer.files);
      }
    });
  }
})();
