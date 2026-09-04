(function () {
  function toast(msg) {
    var el = document.createElement("div");
    el.textContent = msg;
    el.setAttribute("role", "status");
    el.style.cssText =
      "position:fixed;bottom:1.25rem;left:50%;transform:translateX(-50%);background:#0b1220;color:#fff;padding:0.75rem 1.25rem;border-radius:999px;font-size:0.875rem;z-index:9999;font-family:Sora,system-ui,sans-serif;";
    document.body.appendChild(el);
    setTimeout(function () {
      el.remove();
    }, 2800);
  }

  document.querySelectorAll("[data-action], #openInOsBtn, #dropZone, #fileInput").forEach(function (el) {
    el.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      toast("Disponível apenas no app SwiftSend (rede local).");
    });
  });
})();
