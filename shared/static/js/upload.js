(function () {
  const fileInput = document.getElementById("fileInput");
  const folderInput = document.getElementById("folderInput");
  const folderPickBtn = document.getElementById("folderPickBtn");
  const fileNameDisplay = document.getElementById("fileNameDisplay");
  const fileChipIcon = document.getElementById("fileChipIcon");
  const fileList = document.getElementById("fileList");
  const form = document.getElementById("uploadForm");
  const progressBar = document.getElementById("progressBar");
  const progressContainer = document.getElementById("progressContainer");
  const progressPct = document.getElementById("progressPct");
  const progressStats = document.getElementById("progressStats");
  const progressSpeed = document.getElementById("progressSpeed");
  const progressEta = document.getElementById("progressEta");
  const statusText = document.getElementById("statusText");
  const submitBtn = document.getElementById("submitBtn");
  const dropZone = document.getElementById("dropZone");
  const successPanel = document.getElementById("successPanel");

  if (!fileInput || !form) return;

  var pendingFolder = null;

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
    if (progressStats) {
      progressStats.textContent = speedText + " · ETA " + etaText;
    }
    if (statusText && bytesText != null) statusText.textContent = bytesText;
  }

  function setBusy(busy) {
    submitBtn.disabled = busy;
    if (busy) submitBtn.classList.add("opacity-50", "cursor-not-allowed");
    else submitBtn.classList.remove("opacity-50", "cursor-not-allowed");
    if (folderPickBtn) folderPickBtn.disabled = busy;
    fileInput.disabled = busy;
  }

  function showSelection(label, icon) {
    fileList.classList.remove("hidden");
    if (successPanel) successPanel.classList.add("hidden");
    fileNameDisplay.textContent = label;
    if (fileChipIcon) fileChipIcon.textContent = icon || "attach_file";
  }

  function clearFolderPending() {
    pendingFolder = null;
    window.__swiftSendLooseFiles = null;
    if (folderInput) folderInput.value = "";
  }

  function setFolderPending(entries, folderName) {
    if (!entries || !entries.length) {
      window.alert("Pasta vazia ou sem arquivos legíveis.");
      return;
    }
    window.__swiftSendLooseFiles = null;
    pendingFolder = {
      entries: entries,
      folderName: folderName || (window.SwiftSendZip && window.SwiftSendZip.folderNameFromEntries(entries)) || "pasta",
    };
    fileInput.value = "";
    fileInput.removeAttribute("required");
    showSelection(
      "Pasta “" + pendingFolder.folderName + "” · " + entries.length + " arquivo(s) → ZIP",
      "folder_zip"
    );
  }

  function updateFileName() {
    clearFolderPending();
    fileInput.setAttribute("required", "required");
    if (fileInput.files.length > 0) {
      if (fileInput.files.length === 1) {
        showSelection(fileInput.files[0].name, "attach_file");
      } else {
        showSelection(fileInput.files.length + " arquivos selecionados", "attach_file");
      }
    } else {
      fileList.classList.add("hidden");
    }
  }

  fileInput.addEventListener("change", updateFileName);

  if (folderPickBtn && folderInput) {
    folderPickBtn.addEventListener("click", function () {
      folderInput.click();
    });
    folderInput.addEventListener("change", function () {
      if (!folderInput.files.length || !window.SwiftSendZip) return;
      var entries = window.SwiftSendZip.entriesFromFileList(folderInput.files);
      setFolderPending(entries, window.SwiftSendZip.folderNameFromEntries(entries));
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
      if (!e.dataTransfer) return;
      if (!window.SwiftSendZip) {
        if (e.dataTransfer.files.length) {
          fileInput.files = e.dataTransfer.files;
          updateFileName();
        }
        return;
      }
      window.SwiftSendZip
        .collectFromDataTransfer(e.dataTransfer)
        .then(function (result) {
          if (result.kind === "folder") {
            setFolderPending(result.entries, result.folderName);
            return;
          }
          if (result.entries.length) {
            clearFolderPending();
            fileInput.removeAttribute("required");
            window.__swiftSendLooseFiles = result.entries.map(function (item) {
              return item.file;
            });
            try {
              fileInput.files = e.dataTransfer.files;
              if (fileInput.files && fileInput.files.length) {
                window.__swiftSendLooseFiles = null;
                fileInput.setAttribute("required", "required");
                updateFileName();
                return;
              }
            } catch (_err) {
              /* DataTransfer assignment may fail in some WebViews */
            }
            showSelection(
              result.entries.length === 1
                ? result.entries[0].file.name
                : result.entries.length + " arquivos selecionados",
              "attach_file"
            );
          }
        })
        .catch(function (err) {
          window.alert(err.message || "Não foi possível ler a pasta.");
        });
    });
  }

  function sendFormData(formData) {
    const xhr = new XMLHttpRequest();
    var startedAt = Date.now();
    var lastLoaded = 0;
    var lastAt = startedAt;

    if (successPanel) successPanel.classList.add("hidden");
    progressContainer.classList.remove("hidden");
    statusText.classList.remove("hidden");
    statusText.classList.remove("text-success", "text-danger");
    setMeter("0%", "—", "—", "Iniciando envio…");
    progressBar.style.width = "0%";
    setBusy(true);

    xhr.upload.onprogress = function (e) {
      if (!e.lengthComputable) return;
      var now = Date.now();
      var percent = (e.loaded / e.total) * 100;
      progressBar.style.width = percent + "%";

      var dt = (now - lastAt) / 1000;
      var speed = dt > 0 ? (e.loaded - lastLoaded) / dt : 0;
      if (dt >= 0.25) {
        lastLoaded = e.loaded;
        lastAt = now;
      }
      var elapsed = (now - startedAt) / 1000;
      var avgSpeed = elapsed > 0 ? e.loaded / elapsed : 0;
      var remaining = avgSpeed > 0 ? (e.total - e.loaded) / avgSpeed : NaN;
      var showSpeed = speed > 0 ? speed : avgSpeed;

      setMeter(
        Math.round(percent) + "%",
        formatBytes(showSpeed) + "/s",
        formatEta(remaining),
        formatBytes(e.loaded) + " de " + formatBytes(e.total)
      );
    };

    xhr.onload = function () {
      if (xhr.status === 200) {
        progressBar.style.width = "100%";
        setMeter("100%", "concluído", "0s", "");
        statusText.classList.add("text-success");
        if (successPanel) successPanel.classList.remove("hidden");
        setTimeout(function () {
          window.location.reload();
        }, 2200);
      } else {
        statusText.textContent = "Erro ao enviar. Tente novamente.";
        statusText.classList.add("text-danger");
        setBusy(false);
      }
    };

    xhr.onerror = function () {
      statusText.textContent = "Erro de rede ao enviar.";
      statusText.classList.add("text-danger");
      setBusy(false);
    };

    xhr.open("POST", "/api/upload", true);
    xhr.send(formData);
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    var looseFiles = window.__swiftSendLooseFiles;
    if (pendingFolder && window.SwiftSendZip) {
      progressContainer.classList.remove("hidden");
      statusText.classList.remove("hidden", "text-success", "text-danger");
      setMeter("0%", "—", "—", "Compactando pasta…");
      progressBar.style.width = "0%";
      setBusy(true);
      window.SwiftSendZip
        .zipEntries(pendingFolder.entries, { name: pendingFolder.folderName })
        .then(function (zipFile) {
          var formData = new FormData();
          formData.append("file", zipFile, zipFile.name);
          sendFormData(formData);
        })
        .catch(function (err) {
          statusText.textContent = err.message || "Falha ao criar o ZIP.";
          statusText.classList.add("text-danger");
          setBusy(false);
        });
      return;
    }

    if (looseFiles && looseFiles.length) {
      var formDataLoose = new FormData();
      for (var i = 0; i < looseFiles.length; i++) {
        formDataLoose.append("file", looseFiles[i]);
      }
      window.__swiftSendLooseFiles = null;
      sendFormData(formDataLoose);
      return;
    }

    if (!fileInput.files.length) return;
    sendFormData(new FormData(form));
  });
})();
