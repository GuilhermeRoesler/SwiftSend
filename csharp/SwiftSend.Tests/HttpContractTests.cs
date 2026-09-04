using System.Net;
using System.Net.Http.Headers;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.TestHost;
using Xunit;

namespace SwiftSend.Tests;

[Collection(nameof(AppPathsCollection))]
public sealed class HttpContractTests : IAsyncLifetime
{
    private readonly string _root = Path.Combine(Path.GetTempPath(), "SwiftSendTests", Guid.NewGuid().ToString("N"));
    private IDisposable? _folders;
    private WebApplication? _app;
    private HttpClient? _client;

    public async Task InitializeAsync()
    {
        var upload = Path.Combine(_root, "arquivos_recebidos");
        var pub = Path.Combine(_root, "arquivos_publicos");
        _folders = AppPaths.OverrideFolders(upload, pub);

        _app = WebServer.Build(new WebServerOptions
        {
            Listen = false,
            OpenFolder = _ => { },
            Configure = builder => builder.WebHost.UseTestServer(),
        });
        await _app.StartAsync();
        _client = _app.GetTestServer().CreateClient();
    }

    public async Task DisposeAsync()
    {
        _client?.Dispose();
        if (_app is not null)
            await _app.DisposeAsync();
        _folders?.Dispose();
        if (Directory.Exists(_root))
            Directory.Delete(_root, recursive: true);
    }

    private HttpClient Client => _client ?? throw new InvalidOperationException("Client not ready");

    [Fact]
    public async Task Dashboard_OnLocalhost()
    {
        using var request = new HttpRequestMessage(HttpMethod.Get, "/");
        request.Headers.Host = "127.0.0.1:5000";
        using var response = await Client.SendAsync(request);
        var body = await response.Content.ReadAsStringAsync();

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Contains("Servidor ativo", body);
        Assert.Contains("http://", body);
    }

    [Fact]
    public async Task Home_OnLanHost()
    {
        using var request = new HttpRequestMessage(HttpMethod.Get, "/");
        request.Headers.Host = "192.168.0.10:5000";
        using var response = await Client.SendAsync(request);
        var body = await response.Content.ReadAsStringAsync();

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Contains("Transferência na LAN", body);
        Assert.DoesNotContain("Servidor ativo", body);
    }

    [Fact]
    public async Task Browse_ListsPublicFiles()
    {
        await File.WriteAllTextAsync(Path.Combine(AppPaths.PublicFolder, "demo.txt"), "hello");

        using var response = await Client.GetAsync("/browse");
        var body = await response.Content.ReadAsStringAsync();

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Contains("demo.txt", body);
    }

    [Fact]
    public async Task UploadPage_ReturnsOk()
    {
        using var response = await Client.GetAsync("/upload");
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }

    [Fact]
    public async Task ApiUpload_SavesWithTimestamp()
    {
        using var content = BuildMultipart(("nota.txt", "payload"u8.ToArray()));
        using var response = await Client.PostAsync("/api/upload", content);
        var json = await response.Content.ReadAsStringAsync();

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Contains("\"success\":true", json.Replace(" ", ""));

        var saved = Directory.GetFiles(AppPaths.UploadFolder);
        Assert.Single(saved);
        Assert.Matches(new Regex(@"^\d{8}_\d{6}_nota\.txt$"), Path.GetFileName(saved[0]));
        Assert.Equal("payload"u8.ToArray(), await File.ReadAllBytesAsync(saved[0]));
    }

    [Fact]
    public async Task ApiUpload_MultipleFiles()
    {
        using var content = BuildMultipart(
            ("a.txt", "aa"u8.ToArray()),
            ("b.txt", "bb"u8.ToArray()));
        using var response = await Client.PostAsync("/api/upload", content);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal(2, Directory.GetFiles(AppPaths.UploadFolder).Length);
    }

    [Fact]
    public async Task ApiUpload_WithoutFile_Returns400()
    {
        using var content = new MultipartFormDataContent();
        content.Add(new StringContent("1"), "notfile");
        using var response = await Client.PostAsync("/api/upload", content);
        var json = await response.Content.ReadAsStringAsync();

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        using var doc = JsonDocument.Parse(json);
        Assert.True(doc.RootElement.TryGetProperty("error", out _));
    }

    [Fact]
    public async Task Download_Attachment()
    {
        await File.WriteAllBytesAsync(Path.Combine(AppPaths.PublicFolder, "arquivo.bin"), "abc"u8.ToArray());

        using var response = await Client.GetAsync("/download/arquivo.bin");
        var bytes = await response.Content.ReadAsByteArrayAsync();

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("abc"u8.ToArray(), bytes);
        Assert.Contains("attachment", response.Content.Headers.ContentDisposition?.ToString() ?? "",
            StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task Download_Missing_Returns404()
    {
        using var response = await Client.GetAsync("/download/missing.bin");
        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }

    [Fact]
    public async Task Download_RejectsPathTraversal()
    {
        var outside = Path.Combine(_root, "secret.txt");
        await File.WriteAllTextAsync(outside, "nope");

        using var response = await Client.GetAsync("/download/../secret.txt");
        Assert.True(
            response.StatusCode is HttpStatusCode.NotFound or HttpStatusCode.BadRequest,
            $"Unexpected status: {response.StatusCode}");
    }

    [Fact]
    public async Task ManagerRoutes_Redirect()
    {
        using var upload = await Client.GetAsync("/upload_manager");
        using var pub = await Client.GetAsync("/public_manager");

        Assert.Equal(HttpStatusCode.Redirect, upload.StatusCode);
        Assert.Equal(HttpStatusCode.Redirect, pub.StatusCode);
    }

    [Fact]
    public async Task StaticCss_Served()
    {
        using var response = await Client.GetAsync("/static/css/app.css");
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }

    private static MultipartFormDataContent BuildMultipart(params (string fileName, byte[] data)[] files)
    {
        var content = new MultipartFormDataContent();
        foreach (var (fileName, data) in files)
        {
            var part = new ByteArrayContent(data);
            part.Headers.ContentType = new MediaTypeHeaderValue("application/octet-stream");
            content.Add(part, "file", fileName);
        }

        return content;
    }
}

[CollectionDefinition(nameof(AppPathsCollection), DisableParallelization = true)]
public sealed class AppPathsCollection;
