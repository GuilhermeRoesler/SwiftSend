using System.Diagnostics;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Http.Features;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.FileProviders;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

namespace SwiftSend;

internal static class WebServer
{
    public static WebApplication Build()
    {
        var builder = WebApplication.CreateBuilder(new WebApplicationOptions
        {
            Args = [],
            ContentRootPath = AppPaths.DataRoot,
        });

        builder.Logging.ClearProviders();
        builder.Logging.SetMinimumLevel(LogLevel.Warning);

        builder.WebHost.ConfigureKestrel(options =>
        {
            options.Limits.MaxRequestBodySize = 16L * 1024 * 1024 * 1024;
            options.ListenAnyIP(AppPaths.Port);
        });

        builder.Services.Configure<FormOptions>(options =>
        {
            options.MultipartBodyLengthLimit = 16L * 1024 * 1024 * 1024;
        });

        builder.Services.AddSingleton<TemplateRenderer>();

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
            var host = req.Headers.Host.ToString();
            var isDesktop = host.Contains("localhost", StringComparison.OrdinalIgnoreCase)
                            || host.Contains("127.0.0.1", StringComparison.OrdinalIgnoreCase);

            if (isDesktop)
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

        app.MapGet("/upload_manager", () =>
        {
            OpenFolder(AppPaths.UploadFolder);
            return Results.Redirect("/");
        });

        app.MapGet("/public_manager", () =>
        {
            OpenFolder(AppPaths.PublicFolder);
            return Results.Redirect("/");
        });

        app.MapGet("/browse", async (TemplateRenderer templates) =>
        {
            var files = new List<FileEntry>();
            if (Directory.Exists(AppPaths.PublicFolder))
            {
                foreach (var path in Directory.GetFiles(AppPaths.PublicFolder).OrderBy(Path.GetFileName))
                {
                    var info = new FileInfo(path);
                    files.Add(new FileEntry
                    {
                        name = info.Name,
                        size = AppPaths.FormatSize(info.Length),
                    });
                }
            }

            var html = await templates.RenderAsync("browse.html", new
            {
                files,
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
    }

    private static void OpenFolder(string path)
    {
        Directory.CreateDirectory(path);
        Process.Start(new ProcessStartInfo
        {
            FileName = "explorer.exe",
            Arguments = $"\"{path}\"",
            UseShellExecute = true,
        });
    }

    private static string SanitizeFileName(string name)
    {
        var file = Path.GetFileName(name);
        foreach (var c in Path.GetInvalidFileNameChars())
            file = file.Replace(c, '_');
        return string.IsNullOrWhiteSpace(file) ? "arquivo" : file;
    }
}
