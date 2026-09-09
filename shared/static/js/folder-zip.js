(function (global) {
  "use strict";

  var SKIP_NAMES = { ".DS_Store": 1, "Thumbs.db": 1, "desktop.ini": 1 };
  var INCOMPRESSIBLE = {
    zip: 1,
    gz: 1,
    "7z": 1,
    rar: 1,
    bz2: 1,
    xz: 1,
    png: 1,
    jpg: 1,
    jpeg: 1,
    gif: 1,
    webp: 1,
    avif: 1,
    mp4: 1,
    mkv: 1,
    mov: 1,
    avi: 1,
    webm: 1,
    mp3: 1,
    aac: 1,
    flac: 1,
    ogg: 1,
    pdf: 1,
    woff: 1,
    woff2: 1,
  };

  function normalizePath(path) {
    return String(path || "")
      .replace(/\\/g, "/")
      .replace(/^\/+/, "")
      .replace(/\/+/g, "/");
  }

  function basename(path) {
    var parts = normalizePath(path).split("/");
    return parts[parts.length - 1] || "";
  }

  function folderNameFromEntries(entries) {
    for (var i = 0; i < entries.length; i++) {
      var path = normalizePath(entries[i].path);
      var slash = path.indexOf("/");
      if (slash > 0) return path.slice(0, slash);
    }
    return "pasta";
  }

  function sanitizeZipBase(name) {
    var base = String(name || "pasta")
      .replace(/[<>:"/\\|?*\x00-\x1f]/g, "_")
      .replace(/\.+$/g, "")
      .trim();
    return base || "pasta";
  }

  function extOf(path) {
    var name = basename(path);
    var dot = name.lastIndexOf(".");
    return dot >= 0 ? name.slice(dot + 1).toLowerCase() : "";
  }

  function shouldSkip(path) {
    var name = basename(path);
    if (!name || SKIP_NAMES[name]) return true;
    if (name.startsWith("._")) return true;
    return false;
  }

  function entriesFromFileList(fileList) {
    var out = [];
    if (!fileList || !fileList.length) return out;
    for (var i = 0; i < fileList.length; i++) {
      var file = fileList[i];
      var path = normalizePath(file.webkitRelativePath || file.name);
      if (shouldSkip(path)) continue;
      out.push({ file: file, path: path });
    }
    return out;
  }

  function readAllDirectoryEntries(dirReader) {
    return new Promise(function (resolve, reject) {
      var all = [];
      function readBatch() {
        dirReader.readEntries(function (batch) {
          if (!batch.length) {
            resolve(all);
            return;
          }
          all = all.concat(batch);
          readBatch();
        }, reject);
      }
      readBatch();
    });
  }

  function walkEntry(entry, pathPrefix) {
    return new Promise(function (resolve, reject) {
      if (!entry) {
        resolve([]);
        return;
      }
      if (entry.isFile) {
        entry.file(
          function (file) {
            var path = normalizePath(pathPrefix || file.name);
            if (shouldSkip(path)) {
              resolve([]);
              return;
            }
            resolve([{ file: file, path: path }]);
          },
          reject
        );
        return;
      }
      if (entry.isDirectory) {
        var dirPath = normalizePath(pathPrefix || entry.name);
        readAllDirectoryEntries(entry.createReader())
          .then(function (children) {
            return Promise.all(
              children.map(function (child) {
                var childPath = dirPath + "/" + child.name;
                return walkEntry(child, childPath);
              })
            );
          })
          .then(function (nested) {
            var flat = [];
            nested.forEach(function (list) {
              for (var i = 0; i < list.length; i++) flat.push(list[i]);
            });
            resolve(flat);
          })
          .catch(reject);
        return;
      }
      resolve([]);
    });
  }

  function collectFromDataTransfer(dataTransfer) {
    return new Promise(function (resolve, reject) {
      var items = dataTransfer && dataTransfer.items;
      if (items && items.length && typeof items[0].webkitGetAsEntry === "function") {
        var entryPromises = [];
        var hasDirectory = false;
        for (var i = 0; i < items.length; i++) {
          var entry = items[i].webkitGetAsEntry();
          if (!entry) continue;
          if (entry.isDirectory) hasDirectory = true;
          entryPromises.push(walkEntry(entry, entry.name));
        }
        if (entryPromises.length) {
          Promise.all(entryPromises)
            .then(function (groups) {
              var entries = [];
              groups.forEach(function (group) {
                for (var j = 0; j < group.length; j++) entries.push(group[j]);
              });
              resolve({
                kind: hasDirectory ? "folder" : "files",
                entries: entries,
                folderName: hasDirectory ? folderNameFromEntries(entries) : null,
              });
            })
            .catch(reject);
          return;
        }
      }

      var files = dataTransfer && dataTransfer.files ? Array.prototype.slice.call(dataTransfer.files) : [];
      resolve({
        kind: "files",
        entries: files.map(function (file) {
          return { file: file, path: file.name };
        }),
        folderName: null,
      });
    });
  }

  function createZipStream(path) {
    var fflate = global.fflate;
    if (!fflate) throw new Error("Biblioteca de compactação indisponível.");
    var ext = extOf(path);
    if (INCOMPRESSIBLE[ext]) {
      return new fflate.ZipPassThrough(path);
    }
    if (typeof fflate.AsyncZipDeflate === "function") {
      return new fflate.AsyncZipDeflate(path, { level: 6 });
    }
    return new fflate.ZipDeflate(path, { level: 6 });
  }

  function pushFileToStream(file, stream) {
    if (file.stream && typeof file.stream === "function") {
      var reader = file.stream().getReader();
      function pump() {
        return reader.read().then(function (result) {
          if (result.done) {
            stream.push(new Uint8Array(0), true);
            return;
          }
          stream.push(result.value);
          return pump();
        });
      }
      return pump();
    }
    return file.arrayBuffer().then(function (buf) {
      stream.push(new Uint8Array(buf), true);
    });
  }

  function zipEntries(entries, options) {
    options = options || {};
    return new Promise(function (resolve, reject) {
      var fflate = global.fflate;
      if (!fflate) {
        reject(new Error("Biblioteca de compactação indisponível."));
        return;
      }
      if (!entries || !entries.length) {
        reject(new Error("Pasta vazia ou sem arquivos legíveis."));
        return;
      }

      var zipBase = sanitizeZipBase(options.name || folderNameFromEntries(entries));
      var zipName = zipBase + ".zip";
      var chunks = [];
      var zip = new fflate.Zip(function (err, data, final) {
        if (err) {
          reject(err);
          return;
        }
        chunks.push(data);
        if (final) {
          var blob = new Blob(chunks, { type: "application/zip" });
          resolve(new File([blob], zipName, { type: "application/zip", lastModified: Date.now() }));
        }
      });

      var chain = Promise.resolve();
      entries.forEach(function (entry) {
        chain = chain.then(function () {
          var path = normalizePath(entry.path || entry.file.name);
          if (!path || shouldSkip(path)) return;
          var stream = createZipStream(path);
          if (entry.file && entry.file.lastModified) {
            stream.mtime = entry.file.lastModified;
          }
          zip.add(stream);
          return pushFileToStream(entry.file, stream);
        });
      });

      chain
        .then(function () {
          zip.end();
        })
        .catch(function (err) {
          try {
            zip.terminate();
          } catch (_e) {
            /* ignore */
          }
          reject(err);
        });
    });
  }

  function zipFileList(fileList, options) {
    return zipEntries(entriesFromFileList(fileList), options);
  }

  global.SwiftSendZip = {
    entriesFromFileList: entriesFromFileList,
    collectFromDataTransfer: collectFromDataTransfer,
    folderNameFromEntries: folderNameFromEntries,
    sanitizeZipBase: sanitizeZipBase,
    zipEntries: zipEntries,
    zipFileList: zipFileList,
  };
})(typeof window !== "undefined" ? window : this);
