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
  const successFileList = document.getElementById("successFileList");
  const successManageHint = document.getElementById("successManageHint");
  const sendAnotherBtn = document.getElementById("sendAnotherBtn");
  const replaceInput = document.getElementById("replaceInput");

  if (!fileInput || !form) return;

  var pendingFolder = null;
  var manageTimer = null;
  var manageDeadline = 0;
  var pendingReplaceTarget = null;

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

  function formatRemain(seconds) {
    if (seconds <= 0) return "0s";
    if (seconds < 60) return Math.round(seconds) + "s";
    var m = Math.floor(seconds / 60);
    var s = Math.round(seconds % 60);
    if (s === 0) return m + " min";
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

  function stopManageTimer() {
    if (manageTimer) {
      clearInterval(manageTimer);
      manageTimer = null;
    }
    manageDeadline = 0;
  }

  function clearManageUi() {
    stopManageTimer();
    if (successFileList) {
      successFileList.innerHTML = "";
      successFileList.hidden = true;
    }
    if (successManageHint) {
      successManageHint.textContent = "";
      successManageHint.hidden = true;
    }
  }

  function updateManageHint() {
    if (!successManageHint || !manageDeadline) return;
    var remain = Math.max(0, Math.round((manageDeadline - Date.now()) / 1000));
    if (remain <= 0) {
      successManageHint.textContent = "Janela de desfazer encerrada. Peça ao host se precisar corrigir.";
      if (successFileList) {
        var buttons = successFileList.querySelectorAll("button");
        for (var i = 0; i < buttons.length; i++) buttons[i].disabled = true;
      }
      stopManageTimer();
      return;
    }
    successManageHint.hidden = false;
    successManageHint.textContent =
      "Você pode remover ou substituir estes envios por mais " + formatRemain(remain) + ".";
  }

  function renderReceipt(files, manageSeconds) {
    clearManageUi();
    if (!successFileList || !files || !files.length) return;

    successFileList.hidden = false;
    for (var i = 0; i < files.length; i++) {
      (function (item) {
        var li = document.createElement("li");
        li.className = "upload-receipt-item";
        li.dataset.token = item.token || "";
        li.dataset.name = item.name || "";

        var nameEl = document.createElement("span");
        nameEl.className = "upload-receipt-name";
        nameEl.textContent = item.name || "arquivo";

        var actions = document.createElement("div");
        actions.className = "upload-receipt-actions";

        var replaceBtn = document.createElement("button");
        replaceBtn.type = "button";
        replaceBtn.className = "btn-ghost upload-receipt-btn";
        replaceBtn.textContent = "Substituir";
        replaceBtn.addEventListener("click", function () {
          if (!item.token || !replaceInput) return;
          pendingReplaceTarget = { token: item.token, name: item.name, row: li };
          replaceInput.value = "";
          replaceInput.click();
        });

        var undoBtn = document.createElement("button");
        undoBtn.type = "button";
        undoBtn.className = "btn-ghost upload-receipt-btn";
        undoBtn.textContent = "Remover";
        undoBtn.addEventListener("click", function () {
          undoUpload(item.token, li, item.name);
        });

        actions.appendChild(replaceBtn);
        actions.appendChild(undoBtn);
        li.appendChild(nameEl);
        li.appendChild(actions);
        successFileList.appendChild(li);
      })(files[i]);
    }

    var seconds = typeof manageSeconds === "number" && manageSeconds > 0 ? manageSeconds : 600;
    manageDeadline = Date.now() + seconds * 1000;
    updateManageHint();
    manageTimer = setInterval(updateManageHint, 1000);
  }

  function undoUpload(token, row, name) {
    if (!token) return;
    fetch("/api/upload/undo", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: token }),
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (result) {
        if (!result.ok) {
          window.alert((result.data && result.data.error) || "Não foi possível remover.");
          return;
        }
        if (row && row.parentNode) row.parentNode.removeChild(row);
        if (successFileList && !successFileList.children.length) {
          clearManageUi();
          if (successManageHint) {
            successManageHint.hidden = false;
            successManageHint.textContent =
              (name || "Arquivo") + " removido. Você pode enviar de novo quando quiser.";
          }
        }
      })
      .catch(function () {
        window.alert("Erro de rede ao remover.");
      });
  }

  function resetForAnother() {
    clearManageUi();
    if (successPanel) successPanel.classList.add("hidden");
    progressContainer.classList.add("hidden");
    statusText.classList.add("hidden");
    statusText.classList.remove("text-success", "text-danger");
    clearFolderPending();
    fileInput.value = "";
    fileInput.setAttribute("required", "required");
    fileList.classList.add("hidden");
    setBusy(false);
    submitBtn.classList.remove("hidden");
  }

  if (sendAnotherBtn) {
    sendAnotherBtn.addEventListener("click", resetForAnother);
  }

  if (replaceInput) {
    replaceInput.addEventListener("change", function () {
      if (!pendingReplaceTarget || !replaceInput.files || !replaceInput.files.length) {
        pendingReplaceTarget = null;
        return;
      }
      var target = pendingReplaceTarget;
      pendingReplaceTarget = null;
      var file = replaceInput.files[0];
      var formData = new FormData();
      formData.append("file", file, target.name || file.name);
      formData.append("replace", "1");
      sendFormData(formData, { replace: true });
    });
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

  function confirmReplace(names) {
    var list = (names || []).join(", ");
    return window.confirm(
      "Já existe no host: " +
        list +
        ".\n\nSubstituir o arquivo existente? (Cancelar mantém o original e não envia.)"
    );
  }

  function sendFormData(formData, options) {
    options = options || {};
    const xhr = new XMLHttpRequest();
    var startedAt = Date.now();
    var lastLoaded = 0;
    var lastAt = startedAt;
    var replace = !!options.replace;

    if (replace) formData.set("replace", "1");

    if (successPanel) successPanel.classList.add("hidden");
    progressContainer.classList.remove("hidden");
    statusText.classList.remove("hidden");
    statusText.classList.remove("text-success", "text-danger");
    setMeter("0%", "—", "—", "Iniciando envio…");
    progressBar.style.width = "0%";
    setBusy(true);
    submitBtn.classList.add("hidden");

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
      var payload = null;
      try {
        payload = JSON.parse(xhr.responseText || "{}");
      } catch (_err) {
        payload = null;
      }

      if (xhr.status === 409 && payload && payload.exists && !replace) {
        setBusy(false);
        submitBtn.classList.remove("hidden");
        progressContainer.classList.add("hidden");
        if (confirmReplace(payload.names || [])) {
          formData.set("replace", "1");
          sendFormData(formData, { replace: true });
        } else {
          statusText.classList.remove("hidden");
          statusText.textContent = "Envio cancelado — o arquivo original foi mantido.";
          statusText.classList.add("text-danger");
        }
        return;
      }

      if (xhr.status === 200) {
        progressBar.style.width = "100%";
        setMeter("100%", "concluído", "0s", "");
        statusText.classList.add("text-success");
        statusText.classList.add("hidden");
        progressContainer.classList.add("hidden");
        if (successPanel) successPanel.classList.remove("hidden");
        renderReceipt(
          payload && payload.files ? payload.files : [],
          payload && payload.manage_seconds
        );
        setBusy(false);
        clearFolderPending();
        fileInput.value = "";
        fileList.classList.add("hidden");
      } else {
        statusText.classList.remove("hidden");
        statusText.textContent =
          (payload && payload.error) || "Erro ao enviar. Tente novamente.";
        statusText.classList.add("text-danger");
        setBusy(false);
        submitBtn.classList.remove("hidden");
      }
    };

    xhr.onerror = function () {
      statusText.classList.remove("hidden");
      statusText.textContent = "Erro de rede ao enviar.";
      statusText.classList.add("text-danger");
      setBusy(false);
      submitBtn.classList.remove("hidden");
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
