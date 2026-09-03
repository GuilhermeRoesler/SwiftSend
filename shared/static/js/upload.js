(function () {
  const fileInput = document.getElementById("fileInput");
  const fileNameDisplay = document.getElementById("fileNameDisplay");
  const fileList = document.getElementById("fileList");
  const form = document.getElementById("uploadForm");
  const progressBar = document.getElementById("progressBar");
  const progressContainer = document.getElementById("progressContainer");
  const statusText = document.getElementById("statusText");
  const submitBtn = document.getElementById("submitBtn");

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

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    const formData = new FormData(form);
    const xhr = new XMLHttpRequest();

    progressContainer.classList.remove("hidden");
    statusText.classList.remove("hidden");
    statusText.classList.remove("text-green-600", "text-red-600");
    statusText.textContent = "Iniciando upload...";
    submitBtn.disabled = true;
    submitBtn.classList.add("opacity-50", "cursor-not-allowed");

    xhr.upload.onprogress = function (e) {
      if (e.lengthComputable) {
        const percentComplete = (e.loaded / e.total) * 100;
        progressBar.style.width = percentComplete + "%";
        statusText.textContent = Math.round(percentComplete) + "% enviado";
      }
    };

    xhr.onload = function () {
      if (xhr.status === 200) {
        statusText.textContent = "Envio concluído com sucesso!";
        statusText.classList.add("text-green-600");
        setTimeout(function () {
          window.location.reload();
        }, 2000);
      } else {
        statusText.textContent = "Erro ao enviar.";
        statusText.classList.add("text-red-600");
        submitBtn.disabled = false;
        submitBtn.classList.remove("opacity-50", "cursor-not-allowed");
      }
    };

    xhr.onerror = function () {
      statusText.textContent = "Erro ao enviar.";
      statusText.classList.add("text-red-600");
      submitBtn.disabled = false;
      submitBtn.classList.remove("opacity-50", "cursor-not-allowed");
    };

    xhr.open("POST", "/api/upload", true);
    xhr.send(formData);
  });
})();
