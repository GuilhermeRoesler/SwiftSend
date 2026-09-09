(function () {
  function iconForFilename(name) {
    var ext = String(name || "").split(".").pop().toLowerCase();
    var map = {
      pdf: { icon: "picture_as_pdf", cls: "is-doc" },
      doc: { icon: "description", cls: "is-doc" },
      docx: { icon: "description", cls: "is-doc" },
      txt: { icon: "description", cls: "is-doc" },
      md: { icon: "description", cls: "is-doc" },
      xls: { icon: "table", cls: "is-doc" },
      xlsx: { icon: "table", cls: "is-doc" },
      csv: { icon: "table", cls: "is-doc" },
      ppt: { icon: "slideshow", cls: "is-doc" },
      pptx: { icon: "slideshow", cls: "is-doc" },
      zip: { icon: "folder_zip", cls: "is-archive" },
      rar: { icon: "folder_zip", cls: "is-archive" },
      "7z": { icon: "folder_zip", cls: "is-archive" },
      gz: { icon: "folder_zip", cls: "is-archive" },
      tar: { icon: "folder_zip", cls: "is-archive" },
      png: { icon: "image", cls: "is-image" },
      jpg: { icon: "image", cls: "is-image" },
      jpeg: { icon: "image", cls: "is-image" },
      gif: { icon: "image", cls: "is-image" },
      webp: { icon: "image", cls: "is-image" },
      svg: { icon: "image", cls: "is-image" },
      mp4: { icon: "movie", cls: "is-video" },
      mov: { icon: "movie", cls: "is-video" },
      mkv: { icon: "movie", cls: "is-video" },
      webm: { icon: "movie", cls: "is-video" },
      avi: { icon: "movie", cls: "is-video" },
      mp3: { icon: "audio_file", cls: "is-audio" },
      wav: { icon: "audio_file", cls: "is-audio" },
      flac: { icon: "audio_file", cls: "is-audio" },
      aac: { icon: "audio_file", cls: "is-audio" },
      js: { icon: "code", cls: "is-code" },
      ts: { icon: "code", cls: "is-code" },
      py: { icon: "code", cls: "is-code" },
      json: { icon: "data_object", cls: "is-code" },
      html: { icon: "code", cls: "is-code" },
      css: { icon: "code", cls: "is-code" },
      exe: { icon: "terminal", cls: "is-code" },
      msi: { icon: "terminal", cls: "is-code" },
    };
    return map[ext] || { icon: "draft", cls: "" };
  }

  function applyFileIcons() {
    document.querySelectorAll("[data-filename]").forEach(function (row) {
      var name = row.getAttribute("data-filename") || "";
      var meta = iconForFilename(name);
      var wrap = row.querySelector("[data-file-icon]");
      if (!wrap) return;
      if (meta.cls) wrap.classList.add(meta.cls);
      var icon = wrap.querySelector(".material-symbols-outlined");
      if (icon) icon.textContent = meta.icon;
    });
  }

  function bindCopyButtons() {
    document.querySelectorAll("[data-copy]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var text = btn.getAttribute("data-copy") || "";
        function markCopied() {
          btn.classList.add("copied");
          var icon = btn.querySelector(".material-symbols-outlined");
          if (icon) icon.textContent = "check";
          setTimeout(function () {
            btn.classList.remove("copied");
            if (icon) icon.textContent = "content_copy";
          }, 1600);
        }
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(markCopied).catch(function () {
            fallbackCopy(text, markCopied);
          });
        } else {
          fallbackCopy(text, markCopied);
        }
      });
    });
  }

  function fallbackCopy(text, done) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "absolute";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand("copy");
      done();
    } catch (e) {
      /* ignore */
    }
    document.body.removeChild(ta);
  }

  function renderQr() {
    var el = document.getElementById("qrcode");
    if (!el || typeof qrcode !== "function") return;
    var url = el.getAttribute("data-qr") || "";
    if (!url) return;
    try {
      var qr = qrcode(0, "M");
      qr.addData(url);
      qr.make();
      el.innerHTML = qr.createSvgTag({ cellSize: 4, margin: 2, scalable: true });
      var svg = el.querySelector("svg");
      if (svg) {
        svg.setAttribute("width", "100%");
        svg.setAttribute("height", "100%");
        svg.style.width = "100%";
        svg.style.height = "100%";
        svg.style.display = "block";
      }
    } catch (e) {
      el.innerHTML =
        '<span class="material-symbols-outlined text-4xl text-muted-soft" aria-hidden="true">qr_code_2</span>';
    }
  }

  function bindUpdateButton() {
    var btn = document.getElementById("updateBtn");
    if (!btn) return;

    var label = btn.querySelector(".update-btn-label");
    var icon = btn.querySelector(".material-symbols-outlined");
    var latestVersion = "";

    function setBusy(busy, text) {
      btn.disabled = !!busy;
      btn.classList.toggle("is-busy", !!busy);
      if (label && text) label.textContent = text;
      if (icon) icon.textContent = busy ? "progress_activity" : "system_update";
    }

    function showAvailable(latest) {
      latestVersion = latest || "";
      btn.hidden = false;
      btn.title = latestVersion
        ? "Atualizar para a versão " + latestVersion
        : "Atualizar para a versão mais recente";
      if (label) {
        label.textContent = latestVersion ? "Atualizar " + latestVersion : "Atualizar";
      }
    }

    function pollStatus(attempt) {
      var n = attempt || 0;
      fetch("/api/host/update", { headers: { Accept: "application/json" } })
        .then(function (res) {
          if (!res.ok) throw new Error("status " + res.status);
          return res.json();
        })
        .then(function (data) {
          if (data && data.available) {
            showAvailable(data.latest || "");
            return;
          }
          if (data && data.checked) return;
          if (n < 8) {
            setTimeout(function () {
              pollStatus(n + 1);
            }, 700);
          }
        })
        .catch(function () {
          /* silencioso: sem rede / demo estático */
        });
    }

    btn.addEventListener("click", function () {
      if (btn.disabled) return;
      setBusy(true, "Baixando…");
      fetch("/api/host/update", {
        method: "POST",
        headers: { Accept: "application/json" },
      })
        .then(function (res) {
          return res.json().then(function (data) {
            return { ok: res.ok, data: data };
          });
        })
        .then(function (result) {
          if (!result.ok || !result.data || !result.data.success) {
            var err =
              (result.data && result.data.error) || "Não foi possível iniciar a atualização";
            setBusy(false, latestVersion ? "Atualizar " + latestVersion : "Atualizar");
            window.alert(err);
            return;
          }
          setBusy(true, "Encerrando…");
        })
        .catch(function () {
          setBusy(false, latestVersion ? "Atualizar " + latestVersion : "Atualizar");
          window.alert("Falha de rede ao atualizar.");
        });
    });

    pollStatus(0);
  }

  applyFileIcons();
  bindCopyButtons();
  renderQr();
  bindUpdateButton();
})();
