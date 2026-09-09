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
    private static Action<string> _openFolder = FileSystemUtil.DefaultOpenFolder;
    private static UpdateService? _updates;

    public static UpdateService Updates =>
        _updates ??= new UpdateService(AppPaths.AppVersion, AppPaths.ScriptsDir);

    public static WebApplication Build(WebServerOptions? options = null)
    {
        options ??= WebServerOptions.Default;
        _openFolder = options.OpenFolder ?? FileSystemUtil.DefaultOpenFolder;
        _updates ??= new UpdateService(AppPaths.AppVersion, AppPaths.ScriptsDir);

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
                page_sub = "Arquivos enviados pelos visitantes — apague ou renomeie se pedirem correção, ou adicione aqui.",
                empty_hint = "Nada recebido ainda. Visitantes enviam pela página Enviar, ou arraste arquivos acima.",
                files = FileSystemUtil.ListFolderFiles(AppPaths.UploadFolder),
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
                files = FileSystemUtil.ListFolderFiles(AppPaths.PublicFolder),
                is_desktop = true,
            });
            return Results.Content(html, "text/html; charset=utf-8");
        });

        app.MapGet("/browse", async (TemplateRenderer templates) =>
        {
            var html = await templates.RenderAsync("browse.html", new
            {
                files = FileSystemUtil.ListFolderFiles(AppPaths.PublicFolder),
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

            var replace = FileSystemUtil.WantsReplace(form["replace"].ToString());
            var prepared = new List<(IFormFile File, string Name)>();
            foreach (var file in uploads)
            {
                if (string.IsNullOrWhiteSpace(file.FileName))
                    continue;
                // Mesma regra do Python sanitize_basename: vazio / . / .. → ignora.
                var safe = FileSystemUtil.TrySanitizeFileName(file.FileName);
                if (safe is null)
                    continue;
                prepared.Add((file, safe));
            }

            if (prepared.Count == 0)
                return Results.Json(new { error = "No file part" }, statusCode: 400);

            var collisions = prepared
                .Select(p => p.Name)
                .Where(name => File.Exists(Path.Combine(AppPaths.UploadFolder, name)))
                .Distinct(StringComparer.Ordinal)
                .OrderBy(n => n, StringComparer.Ordinal)
                .ToArray();
            if (collisions.Length > 0 && !replace)
            {
                return Results.Json(new
                {
                    error = "Arquivo já existe",
                    exists = true,
                    names = collisions,
                }, statusCode: 409);
            }

            Directory.CreateDirectory(AppPaths.UploadFolder);
            var saved = new List<object>();
            foreach (var (file, name) in prepared)
            {
                var dest = Path.Combine(AppPaths.UploadFolder, name);
                await using (var stream = File.Create(dest))
                    await file.CopyToAsync(stream);
                saved.Add(UploadTokenStore.Issue(name));
            }

            return Results.Json(new
            {
                success = true,
                files = saved,
                manage_seconds = UploadTokenStore.ManageSeconds,
            });
        });

        app.MapPost("/api/upload/undo", async (HttpRequest request) =>
        {
            var body = await ReadJsonAsync(request);
            var name = UploadTokenStore.Consume(GetString(body, "token"));
            if (name is null)
                return Results.Json(new { error = "Token inválido ou expirado" }, statusCode: 404);

            var target = FileSystemUtil.SafePathInFolder(AppPaths.UploadFolder, name);
            if (target is null || !File.Exists(target))
                return Results.Json(new { error = "Arquivo não encontrado" }, statusCode: 404);

            try
            {
                File.Delete(target);
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Falha ao apagar upload undo: {ex.Message}");
                return Results.Json(new { error = "Não foi possível apagar" }, statusCode: 400);
            }

            return Results.Json(new { success = true, name });
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

            var folder = FileSystemUtil.ResolveManagedFolder(req.Query["folder"].ToString());
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
            var folder = FileSystemUtil.ResolveManagedFolder(GetString(body, "folder"));
            var target = folder is null ? null : FileSystemUtil.SafePathInFolder(folder, GetString(body, "name"));
            if (folder is null || target is null)
                return Results.Json(new { error = "Pedido inválido" }, statusCode: 400);
            if (!File.Exists(target))
                return Results.Json(new { error = "Arquivo não encontrado" }, statusCode: 404);

            try
            {
                File.Delete(target);
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Falha ao apagar arquivo host: {ex.Message}");
                return Results.Json(new { error = "Não foi possível apagar" }, statusCode: 400);
            }

            return Results.Json(new { success = true });
        });

        app.MapPost("/api/host/rename", async (HttpRequest req) =>
        {
            if (!IsDesktopHost(req))
                return Results.Json(new { error = "Forbidden" }, statusCode: 403);

            var body = await ReadJsonAsync(req);
            var folder = FileSystemUtil.ResolveManagedFolder(GetString(body, "folder"));
            var src = folder is null ? null : FileSystemUtil.SafePathInFolder(folder, GetString(body, "name"));
            var newName = FileSystemUtil.TrySanitizeFileName(GetString(body, "new_name"));
            if (folder is null || src is null || newName is null)
                return Results.Json(new { error = "Pedido inválido" }, statusCode: 400);
            if (!File.Exists(src))
                return Results.Json(new { error = "Arquivo não encontrado" }, statusCode: 404);

            var dest = FileSystemUtil.SafePathInFolder(folder, newName);
            if (dest is null)
                return Results.Json(new { error = "Nome inválido" }, statusCode: 400);
            if (File.Exists(dest))
                return Results.Json(new { error = "Já existe um arquivo com esse nome" }, statusCode: 409);

            try
            {
                File.Move(src, dest);
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Falha ao renomear arquivo host: {ex.Message}");
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
            var folder = FileSystemUtil.ResolveManagedFolder(form["folder"].ToString());
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

                var trySafe = FileSystemUtil.TrySanitizeFileName(file.FileName);
                if (trySafe is null)
                    continue;

                var dest = FileSystemUtil.UniqueDest(folder, trySafe);
                await using var stream = File.Create(dest);
                await file.CopyToAsync(stream);
                saved++;
            }

            if (saved == 0)
                return Results.Json(new { error = "No file part" }, statusCode: 400);

            return Results.Json(new { success = true });
        });

        app.MapMethods("/api/host/update", ["GET", "POST"], async (HttpRequest req) =>
        {
            if (!IsDesktopHost(req))
                return Results.Json(new { error = "Forbidden" }, statusCode: 403);

            if (HttpMethods.IsGet(req.Method))
                return Results.Json(Updates.Snapshot().ToJson());

            var result = await Updates.ApplyUpdateAsync();
            var ok = result.TryGetValue("success", out var success) && success is true;
            return Results.Json(result, statusCode: ok ? 200 : 400);
        });
    }

    private static bool IsDesktopHost(HttpRequest req)
    {
        var host = req.Headers.Host.ToString();
        return host.Contains("localhost", StringComparison.OrdinalIgnoreCase)
               || host.Contains("127.0.0.1", StringComparison.OrdinalIgnoreCase);
    }

    private static async Task<JsonElement> ReadJsonAsync(HttpRequest req)
    {
        try
        {
            using var doc = await JsonDocument.ParseAsync(req.Body);
            return doc.RootElement.Clone();
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"JSON inválido na request: {ex.Message}");
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
}
