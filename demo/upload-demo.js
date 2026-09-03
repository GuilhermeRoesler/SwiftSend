(function () {
  const fileInput = document.getElementById("fileInput");
  const fileNameDisplay = document.getElementById("fileNameDisplay");
  const fileList = document.getElementById("fileList");
  const form = document.getElementById("uploadForm");
  const progressBar = document.getElementById("progressBar");
  const progressContainer = document.getElementById("progressContainer");
  const statusText = document.getElementById("statusText");
  const submitBtn = document.getElementById("submitBtn");
  const dropZone = document.getElementById("dropZone");

  if (!fileInput || !form) return;

  function updateFileName() {
    if (fileInput.files.length > 0) {
      fileList.classList.remove("hidden");
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

    progressContainer.classList.remove("hidden");
    statusText.classList.remove("hidden", "text-green-600", "text-red-600");
    statusText.textContent = "Simulando envio (demo)...";
    submitBtn.disabled = true;
    submitBtn.classList.add("opacity-50", "cursor-not-allowed");

    var pct = 0;
    var timer = setInterval(function () {
      pct += 8 + Math.floor(Math.random() * 10);
      if (pct >= 100) {
        pct = 100;
        clearInterval(timer);
        progressBar.style.width = "100%";
        statusText.textContent =
          "Demo: arquivo não foi enviado. Use o app SwiftSend na rede local.";
        statusText.classList.add("text-red-600");
        submitBtn.disabled = false;
        submitBtn.classList.remove("opacity-50", "cursor-not-allowed");
        return;
      }
      progressBar.style.width = pct + "%";
      statusText.textContent = pct + "% (simulado)";
    }, 120);
  });
})();
