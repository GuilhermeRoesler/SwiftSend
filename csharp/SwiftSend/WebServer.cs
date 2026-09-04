using System.Diagnostics;
using System.Text.Json;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Http.Features;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.FileProviders;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

namespace SwiftSend;

internal sealed class WebServerOptions
{
    public static WebServerOptions Default { get; } = new();

    /// <summary>Quando true, escuta 0.0.0.0:5000 (produção). Em testes use false + Configure UseTestServer.</summary>
    public bool Listen { get; init; } = true;

    public Action<WebApplicationBuilder>? Configure { get; init; }

    /// <summary>Substitui abertura do Explorer (no-op útil em testes).</summary>
    public Action<string>? OpenFolder { get; init; }
}

internal static class WebServer
{
    private static Action<string> _openFolder = DefaultOpenFolder;

    public static WebApplication Build(WebServerOptions? options = null)
    {
        options ??= WebServerOptions.Default;
        _openFolder = options.OpenFolder ?? DefaultOpenFolder;

        var builder = WebApplication.CreateBuilder(new WebApplicationOptions
        {
            Args = [],
            ContentRootPath = AppPaths.DataRoot,
        });

        builder.Logging.ClearProviders();
        builder.Logging.SetMinimumLevel(LogLevel.Warning);

        builder.WebHost.ConfigureKestrel(kestrel =>
        {
            kestrel.Limits.MaxRequestBodySize = 16L * 1024 * 1024 * 1024;
            if (options.Listen)
                kestrel.ListenAnyIP(AppPaths.Port);
        });

        builder.Services.Configure<FormOptions>(form =>
        {
            form.MultipartBodyLengthLimit = 16L * 1024 * 1024 * 1024;
        });

        builder.Services.AddSingleton<TemplateRenderer>();
        options.Configure?.Invoke(builder);

        var app = builder.Build();

        if (Directory.Exists(AppPaths.StaticDir))
        {
            app.UseStaticFiles(new StaticFileOptions
            {
                FileProvider = new PhysicalFileProvider(AppPaths.StaticDir),
                RequestPath = "/static",
            });
        }

        MapRoutes(app);
        return app;
    }

    private static void MapRoutes(WebApplication app)
    {
        app.MapGet("/", async (HttpRequest req, TemplateRenderer templates) =>
        {
            if (IsDesktopHost(req))
            {
                var count = Directory.Exists(AppPaths.UploadFolder)
                    ? Directory.GetFileSystemEntries(AppPaths.UploadFolder).Length
                    : 0;
                var html = await templates.RenderAsync("dashboard.html", new
                {
                    base_url = AppPaths.BaseUrl,
                    received_count = count,
                    upload_path = AppPaths.UploadFolder,
                    is_desktop = true,
                });
                return Results.Content(html, "text/html; charset=utf-8");
            }

            var home = await templates.RenderAsync("home.html", new { is_desktop = false });
            return Results.Content(home, "text/html; charset=utf-8");
        });

        app.MapGet("/upload_manager", async (HttpRequest req, TemplateRenderer templates) =>
        {
            if (!IsDesktopHost(req))
                return Results.Redirect("/");

            var html = await templates.RenderAsync("manager.html", new
            {
                folder = "received",
                page_title = "Recebidos",
                eyebrow = "Host",
                eyebrow_icon = "inbox",
                page_sub = "Arquivos enviados pelos visitantes — apague, renomeie ou adicione aqui.",
                empty_hint = "Nada recebido ainda. Visitantes enviam pela página Enviar, ou arraste arquivos acima.",
                files = ListFolderFiles(AppPaths.UploadFolder),
                is_desktop = true,
            });
            return Results.Content(html, "text/html; charset=utf-8");
        });

        app.MapGet("/public_manager", async (HttpRequest req, TemplateRenderer templates) =>
        {
            if (!IsDesktopHost(req))
                return Results.Redirect("/");

            var html = await templates.RenderAsync("manager.html", new
            {
                folder = "public",
                page_title = "Públicos",
                eyebrow = "Host",
                eyebrow_icon = "folder_shared",
                page_sub = "O que os visitantes veem em Baixar — gerencie sem sair do app.",
                empty_hint = "Nada público ainda. Arraste arquivos acima para disponibilizar na rede.",
                files = ListFolderFiles(AppPaths.PublicFolder),
                is_desktop = true,
            });
            return Results.Content(html, "text/html; charset=utf-8");
        });

        app.MapGet("/browse", async (TemplateRenderer templates) =>
        {
            var html = await templates.RenderAsync("browse.html", new
            {
                files = ListFolderFiles(AppPaths.PublicFolder),
                is_desktop = false,
            });
            return Results.Content(html, "text/html; charset=utf-8");
        });

        app.MapGet("/upload", async (TemplateRenderer templates) =>
        {
            var html = await templates.RenderAsync("upload.html", new { is_desktop = false });
            return Results.Content(html, "text/html; charset=utf-8");
        });

        app.MapPost("/api/upload", async (HttpRequest request) =>
        {
            if (!request.HasFormContentType)
                return Results.Json(new { error = "No file part" }, statusCode: 400);

            var form = await request.ReadFormAsync();
            var uploads = form.Files.GetFiles("file");
            if (uploads.Count == 0)
                return Results.Json(new { error = "No file part" }, statusCode: 400);

            foreach (var file in uploads)
            {
                if (string.IsNullOrWhiteSpace(file.FileName))
                    continue;

                var safe = SanitizeFileName(file.FileName);
                var stamp = DateTime.Now.ToString("yyyyMMdd_HHmmss_");
                var dest = Path.Combine(AppPaths.UploadFolder, stamp + safe);
                await using var stream = File.Create(dest);
                await file.CopyToAsync(stream);
            }

            return Results.Json(new { success = true });
        });

        app.MapGet("/download/{*filename}", (string filename) =>
        {
            var safeName = Path.GetFileName(filename);
            var full = Path.Combine(AppPaths.PublicFolder, safeName);
            if (!File.Exists(full))
                return Results.NotFound();
            return Results.File(full, fileDownloadName: safeName);
        });

        app.MapGet("/api/host/open", (HttpRequest req) =>
        {
            if (!IsDesktopHost(req))
                return Results.Json(new { error = "Forbidden" }, statusCode: 403);

            var folder = ResolveManagedFolder(req.Query["folder"].ToString());
            if (folder is null)
                return Results.Json(new { error = "Pasta inválida" }, statusCode: 400);

            _openFolder(folder);
            return Results.Json(new { success = true });
        });

        app.MapPost("/api/host/delete", async (HttpRequest req) =>
        {
            if (!IsDesktopHost(req))
                return Results.Json(new { error = "Forbidden" }, statusCode: 403);

            var body = await ReadJsonAsync(req);
            var folder = ResolveManagedFolder(GetString(body, "folder"));
            var target = folder is null ? null : SafePathInFolder(folder, GetString(body, "name"));
            if (folder is null || target is null)
                return Results.Json(new { error = "Pedido inválido" }, statusCode: 400);
            if (!File.Exists(target))
                return Results.Json(new { error = "Arquivo não encontrado" }, statusCode: 404);

            try
            {
                File.Delete(target);
            }
            catch
            {
                return Results.Json(new { error = "Não foi possível apagar" }, statusCode: 400);
            }

            return Results.Json(new { success = true });
        });

        app.MapPost("/api/host/rename", async (HttpRequest req) =>
        {
            if (!IsDesktopHost(req))
                return Results.Json(new { error = "Forbidden" }, statusCode: 403);

            var body = await ReadJsonAsync(req);
            var folder = ResolveManagedFolder(GetString(body, "folder"));
            var src = folder is null ? null : SafePathInFolder(folder, GetString(body, "name"));
            var newName = TrySanitizeFileName(GetString(body, "new_name"));
            if (folder is null || src is null || newName is null)
                return Results.Json(new { error = "Pedido inválido" }, statusCode: 400);
            if (!File.Exists(src))
                return Results.Json(new { error = "Arquivo não encontrado" }, statusCode: 404);

            var dest = SafePathInFolder(folder, newName);
            if (dest is null)
                return Results.Json(new { error = "Nome inválido" }, statusCode: 400);
            if (File.Exists(dest))
                return Results.Json(new { error = "Já existe um arquivo com esse nome" }, statusCode: 409);

            try
            {
                File.Move(src, dest);
            }
            catch
            {
                return Results.Json(new { error = "Não foi possível renomear" }, statusCode: 400);
            }

            return Results.Json(new { success = true });
        });

        app.MapPost("/api/host/upload", async (HttpRequest request) =>
        {
            if (!IsDesktopHost(request))
                return Results.Json(new { error = "Forbidden" }, statusCode: 403);

            if (!request.HasFormContentType)
                return Results.Json(new { error = "No file part" }, statusCode: 400);

            var form = await request.ReadFormAsync();
            var folder = ResolveManagedFolder(form["folder"].ToString());
            if (folder is null)
                return Results.Json(new { error = "Pasta inválida" }, statusCode: 400);

            var uploads = form.Files.GetFiles("file");
            if (uploads.Count == 0)
                return Results.Json(new { error = "No file part" }, statusCode: 400);

            var saved = 0;
            foreach (var file in uploads)
            {
                if (string.IsNullOrWhiteSpace(file.FileName))
                    continue;

                var safe = SanitizeFileName(file.FileName);
                var dest = UniqueDest(folder, safe);
                await using var stream = File.Create(dest);
                await file.CopyToAsync(stream);
                saved++;
            }

            if (saved == 0)
                return Results.Json(new { error = "No file part" }, statusCode: 400);

            return Results.Json(new { success = true });
        });
    }

    private static bool IsDesktopHost(HttpRequest req)
    {
        var host = req.Headers.Host.ToString();
        return host.Contains("localhost", StringComparison.OrdinalIgnoreCase)
               || host.Contains("127.0.0.1", StringComparison.OrdinalIgnoreCase);
    }

    private static string? ResolveManagedFolder(string? kind) => kind switch
    {
        "received" => AppPaths.UploadFolder,
        "public" => AppPaths.PublicFolder,
        _ => null,
    };

    private static List<FileEntry> ListFolderFiles(string folder)
    {
        var files = new List<FileEntry>();
        if (!Directory.Exists(folder))
            return files;

        foreach (var path in Directory.GetFiles(folder).OrderBy(Path.GetFileName))
        {
            var info = new FileInfo(path);
            files.Add(new FileEntry
            {
                name = info.Name,
                size = AppPaths.FormatSize(info.Length),
            });
        }

        return files;
    }

    private static string? SafePathInFolder(string folder, string? name)
    {
        var safe = TrySanitizeFileName(name ?? "");
        if (safe is null)
            return null;

        var folderFull = Path.GetFullPath(folder);
        var full = Path.GetFullPath(Path.Combine(folderFull, safe));
        var relative = Path.GetRelativePath(folderFull, full);
        if (relative.StartsWith("..", StringComparison.Ordinal) || Path.IsPathRooted(relative))
            return null;

        return full;
    }

    private static string UniqueDest(string folder, string filename)
    {
        var dest = Path.Combine(folder, filename);
        if (!File.Exists(dest))
            return dest;

        var stem = Path.GetFileNameWithoutExtension(filename);
        var ext = Path.GetExtension(filename);
        for (var n = 2; ; n++)
        {
            var candidate = Path.Combine(folder, $"{stem}_{n}{ext}");
            if (!File.Exists(candidate))
                return candidate;
        }
    }

    private static async Task<JsonElement> ReadJsonAsync(HttpRequest req)
    {
        try
        {
            using var doc = await JsonDocument.ParseAsync(req.Body);
            return doc.RootElement.Clone();
        }
        catch
        {
            return default;
        }
    }

    private static string GetString(JsonElement body, string name)
    {
        if (body.ValueKind != JsonValueKind.Object)
            return "";
        return body.TryGetProperty(name, out var prop) && prop.ValueKind == JsonValueKind.String
            ? prop.GetString() ?? ""
            : "";
    }

    private static void DefaultOpenFolder(string path)
    {
        Directory.CreateDirectory(path);
        Process.Start(new ProcessStartInfo
        {
            FileName = "explorer.exe",
            Arguments = $"\"{path}\"",
            UseShellExecute = true,
        });
    }

    private static string? TrySanitizeFileName(string name)
    {
        var file = Path.GetFileName(name).Trim();
        if (string.IsNullOrWhiteSpace(file) || file is "." or "..")
            return null;
        foreach (var c in Path.GetInvalidFileNameChars())
            file = file.Replace(c, '_');
        return string.IsNullOrWhiteSpace(file) ? null : file;
    }

    private static string SanitizeFileName(string name)
    {
        return TrySanitizeFileName(name) ?? "arquivo";
    }
}
