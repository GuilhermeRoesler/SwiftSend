(function () {
  const fileInput = document.getElementById("fileInput");
  const fileNameDisplay = document.getElementById("fileNameDisplay");
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

  function updateFileName() {
    if (fileInput.files.length > 0) {
      fileList.classList.remove("hidden");
      if (successPanel) successPanel.classList.add("hidden");
      if (fileInput.files.length === 1) {
        fileNameDisplay.textContent = fileInput.files[0].name;
      } else {
        fileNameDisplay.textContent = fileInput.files.length + " arquivos selecionados";
      }
    }
  }

  fileInput.addEventListener("change", updateFileName);

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
        fileInput.files = e.dataTransfer.files;
        updateFileName();
      }
    });
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    if (!fileInput.files.length) return;

    const formData = new FormData(form);
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
    submitBtn.disabled = true;
    submitBtn.classList.add("opacity-50", "cursor-not-allowed");

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
        submitBtn.disabled = false;
        submitBtn.classList.remove("opacity-50", "cursor-not-allowed");
      }
    };

    xhr.onerror = function () {
      statusText.textContent = "Erro de rede ao enviar.";
      statusText.classList.add("text-danger");
      submitBtn.disabled = false;
      submitBtn.classList.remove("opacity-50", "cursor-not-allowed");
    };

    xhr.open("POST", "/api/upload", true);
    xhr.send(formData);
  });
})();
