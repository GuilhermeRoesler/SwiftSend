using System.Diagnostics;
using System.Net.Http.Headers;
using System.Text.Json;

namespace SwiftSend;

internal sealed class UpdateStatus
{
    public string Current { get; init; } = "0.0.0-dev";
    public string? Latest { get; set; }
    public bool Available { get; set; }
    public string? DownloadUrl { get; set; }
    public string? AssetName { get; set; }
    public bool Checked { get; set; }
    public string? Error { get; set; }
    public bool Applying { get; set; }

    public Dictionary<string, object?> ToJson() => new()
    {
        ["current"] = Current,
        ["latest"] = Latest,
        ["available"] = Available,
        ["download_url"] = DownloadUrl,
        ["asset_name"] = AssetName,
        ["checked"] = Checked,
        ["error"] = Error,
        ["applying"] = Applying,
    };
}

internal sealed class UpdateService
{
    public const string GitHubRepo = "GuilhermeRoesler/SwiftSend";
    public static readonly string ApiLatest = $"https://api.github.com/repos/{GitHubRepo}/releases/latest";
    private const string UserAgent = "SwiftSend-Updater";
    private const int ForceKillTimeoutSec = 10;

    private readonly object _lock = new();
    private readonly UpdateStatus _status;
    private readonly string _scriptsDir;
    private readonly string _downloadDir;
    private readonly Func<string, Task<JsonDocument>> _fetchJson;
    private readonly HttpClient _http;

    public UpdateService(
        string currentVersion,
        string scriptsDir,
        Func<string, Task<JsonDocument>>? fetchJson = null,
        string? downloadDir = null)
    {
        _status = new UpdateStatus { Current = currentVersion };
        _scriptsDir = scriptsDir;
        _downloadDir = downloadDir ?? Path.Combine(Path.GetTempPath(), "SwiftSendUpdates");
        _http = new HttpClient { Timeout = TimeSpan.FromMinutes(10) };
        _http.DefaultRequestHeaders.UserAgent.ParseAdd(UserAgent);
        _http.DefaultRequestHeaders.Accept.Add(new MediaTypeWithQualityHeaderValue("application/vnd.github+json"));
        _fetchJson = fetchJson ?? DefaultFetchJsonAsync;
    }

    public UpdateStatus Snapshot()
    {
        lock (_lock)
        {
            return new UpdateStatus
            {
                Current = _status.Current,
                Latest = _status.Latest,
                Available = _status.Available,
                DownloadUrl = _status.DownloadUrl,
                AssetName = _status.AssetName,
                Checked = _status.Checked,
                Error = _status.Error,
                Applying = _status.Applying,
            };
        }
    }

    public void StartBackgroundCheck()
    {
        _ = Task.Run(async () =>
        {
            try
            {
                await CheckNowAsync().ConfigureAwait(false);
            }
            catch
            {
                // ignore — status already records error
            }
        });
    }

    public async Task<UpdateStatus> CheckNowAsync()
    {
        try
        {
            using var doc = await _fetchJson(ApiLatest).ConfigureAwait(false);
            var root = doc.RootElement;
            var tag = root.TryGetProperty("tag_name", out var tagEl) ? tagEl.GetString()?.Trim() ?? "" : "";
            if (string.IsNullOrWhiteSpace(tag))
                throw new InvalidOperationException("Release sem tag_name");

            string? downloadUrl = null;
            string? assetName = null;
            if (root.TryGetProperty("assets", out var assets) && assets.ValueKind == JsonValueKind.Array)
            {
                foreach (var asset in assets.EnumerateArray())
                {
                    var name = asset.TryGetProperty("name", out var n) ? n.GetString() ?? "" : "";
                    var url = asset.TryGetProperty("browser_download_url", out var u) ? u.GetString() ?? "" : "";
                    if (!string.IsNullOrWhiteSpace(name) && !string.IsNullOrWhiteSpace(url) && MatchesPlatform(name))
                    {
                        downloadUrl = url;
                        assetName = name;
                        break;
                    }
                }
            }

            var latestDisplay = tag.StartsWith('v') || tag.StartsWith('V') ? tag[1..] : tag;
            var newer = IsNewer(tag, _status.Current);
            var available = newer && downloadUrl is not null;

            lock (_lock)
            {
                _status.Latest = latestDisplay;
                _status.Available = available;
                _status.DownloadUrl = downloadUrl;
                _status.AssetName = assetName;
                _status.Checked = true;
                _status.Error = newer && downloadUrl is null ? "Sem artefato para esta plataforma" : null;
                return SnapshotUnlocked();
            }
        }
        catch (Exception ex)
        {
            lock (_lock)
            {
                _status.Checked = true;
                _status.Available = false;
                _status.Error = ex.Message;
                return SnapshotUnlocked();
            }
        }
    }

    public async Task<Dictionary<string, object?>> ApplyUpdateAsync()
    {
        string url;
        string assetName;
        lock (_lock)
        {
            if (_status.Applying)
                return new Dictionary<string, object?> { ["success"] = false, ["error"] = "Atualização já em andamento" };
            if (!_status.Available || string.IsNullOrWhiteSpace(_status.DownloadUrl) || string.IsNullOrWhiteSpace(_status.AssetName))
                return new Dictionary<string, object?> { ["success"] = false, ["error"] = "Nenhuma atualização disponível" };
            _status.Applying = true;
            url = _status.DownloadUrl!;
            assetName = _status.AssetName!;
        }

        try
        {
            var installer = await DownloadAsync(url, assetName).ConfigureAwait(false);
            SpawnApplyScript(installer);
            return new Dictionary<string, object?> { ["success"] = true, ["installer"] = installer };
        }
        catch (Exception ex)
        {
            lock (_lock)
            {
                _status.Applying = false;
            }
            return new Dictionary<string, object?> { ["success"] = false, ["error"] = ex.Message };
        }
    }

    public static string ReadVersion(params string[] searchRoots)
    {
        foreach (var root in searchRoots)
        {
            if (string.IsNullOrWhiteSpace(root))
                continue;
            var candidate = Path.Combine(root, "VERSION");
            if (File.Exists(candidate))
            {
                var text = File.ReadAllText(candidate).Trim();
                if (!string.IsNullOrWhiteSpace(text))
                    return text;
            }
        }

        return "0.0.0-dev";
    }

    public static (int Major, int Minor, int Patch) NormalizeVersion(string tag)
    {
        var raw = (tag ?? "").Trim();
        if (raw.StartsWith('v') || raw.StartsWith('V'))
            raw = raw[1..];
        var core = raw.Split('-', 2)[0].Split('+', 2)[0];
        var parts = new List<int>();
        foreach (var piece in core.Split('.'))
        {
            parts.Add(int.TryParse(piece, out var n) ? n : 0);
        }
        while (parts.Count < 3)
            parts.Add(0);
        return (parts[0], parts[1], parts[2]);
    }

    public static bool IsNewer(string latest, string current)
    {
        var a = NormalizeVersion(latest);
        var b = NormalizeVersion(current);
        var cmp = a.Major.CompareTo(b.Major);
        if (cmp != 0) return cmp > 0;
        cmp = a.Minor.CompareTo(b.Minor);
        if (cmp != 0) return cmp > 0;
        return a.Patch.CompareTo(b.Patch) > 0;
    }

    private UpdateStatus SnapshotUnlocked() => new()
    {
        Current = _status.Current,
        Latest = _status.Latest,
        Available = _status.Available,
        DownloadUrl = _status.DownloadUrl,
        AssetName = _status.AssetName,
        Checked = _status.Checked,
        Error = _status.Error,
        Applying = _status.Applying,
    };

    private async Task<JsonDocument> DefaultFetchJsonAsync(string url)
    {
        using var req = new HttpRequestMessage(HttpMethod.Get, url);
        req.Headers.TryAddWithoutValidation("X-GitHub-Api-Version", "2022-11-28");
        using var resp = await _http.SendAsync(req).ConfigureAwait(false);
        resp.EnsureSuccessStatusCode();
        await using var stream = await resp.Content.ReadAsStreamAsync().ConfigureAwait(false);
        return await JsonDocument.ParseAsync(stream).ConfigureAwait(false);
    }

    private static bool MatchesPlatform(string name)
    {
        var lower = name.ToLowerInvariant();
        if (OperatingSystem.IsWindows())
            return lower.StartsWith("swiftsend-setup-", StringComparison.Ordinal) && lower.EndsWith(".exe", StringComparison.Ordinal);
        if (OperatingSystem.IsMacOS())
            return lower.Contains("macos", StringComparison.Ordinal) && lower.EndsWith(".dmg", StringComparison.Ordinal);
        return lower.Contains("linux", StringComparison.Ordinal) && lower.EndsWith(".appimage", StringComparison.Ordinal);
    }

    private async Task<string> DownloadAsync(string url, string assetName)
    {
        Directory.CreateDirectory(_downloadDir);
        var safeName = Path.GetFileName(assetName);
        var dest = Path.Combine(_downloadDir, safeName);
        using var resp = await _http.GetAsync(url, HttpCompletionOption.ResponseHeadersRead).ConfigureAwait(false);
        resp.EnsureSuccessStatusCode();
        await using var input = await resp.Content.ReadAsStreamAsync().ConfigureAwait(false);
        await using var output = File.Create(dest);
        await input.CopyToAsync(output).ConfigureAwait(false);
        if (new FileInfo(dest).Length <= 0)
            throw new InvalidOperationException("Download vazio");
        return dest;
    }

    private void SpawnApplyScript(string installer)
    {
        var scriptName = OperatingSystem.IsWindows() ? "apply_update.ps1" : "apply_update.sh";
        var src = Path.Combine(_scriptsDir, scriptName);
        if (!File.Exists(src))
        {
            var beside = Path.Combine(AppContext.BaseDirectory, "scripts", scriptName);
            if (File.Exists(beside))
                src = beside;
            else
                throw new FileNotFoundException($"Script de update não encontrado: {scriptName}");
        }

        var staging = Path.Combine(Path.GetTempPath(), scriptName);
        File.Copy(src, staging, overwrite: true);
        var pid = Environment.ProcessId;

        if (OperatingSystem.IsWindows())
        {
            // UseShellExecute=true: processo independente do job do app (sobrevive ao force kill).
            var psi = new ProcessStartInfo
            {
                FileName = "powershell.exe",
                Arguments =
                    $"-NoProfile -ExecutionPolicy Bypass -File \"{staging}\" -TargetPid {pid} -Installer \"{installer}\" -TimeoutSec {ForceKillTimeoutSec}",
                UseShellExecute = true,
                WindowStyle = ProcessWindowStyle.Hidden,
                WorkingDirectory = Path.GetTempPath(),
            };
            Process.Start(psi);
        }
        else
        {
            try
            {
                File.SetUnixFileMode(staging, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
            }
            catch
            {
                // ignore on platforms without chmod semantics
            }

            var psi = new ProcessStartInfo
            {
                FileName = "/bin/bash",
                ArgumentList = { staging, pid.ToString(), installer, ForceKillTimeoutSec.ToString() },
                UseShellExecute = false,
                CreateNoWindow = true,
            };
            Process.Start(psi);
        }
    }
}
