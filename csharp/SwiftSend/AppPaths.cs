namespace SwiftSend;

internal static class AppPaths
{
    public const int Port = 5000;

    public static string DataRoot { get; }
    public static string SharedDir { get; }
    public static string TemplatesDir { get; }
    public static string StaticDir { get; }
    public static string UploadFolder { get; }
    public static string PublicFolder { get; }
    public static string LocalIp { get; }
    public static string BaseUrl { get; }

    static AppPaths()
    {
        DataRoot = ResolveDataRoot();
        SharedDir = ResolveSharedDir(DataRoot);
        TemplatesDir = Path.Combine(SharedDir, "templates");
        StaticDir = Path.Combine(SharedDir, "static");
        UploadFolder = Path.Combine(DataRoot, "arquivos_recebidos");
        PublicFolder = Path.Combine(DataRoot, "arquivos_publicos");
        Directory.CreateDirectory(UploadFolder);
        Directory.CreateDirectory(PublicFolder);
        LocalIp = GetLocalIp();
        BaseUrl = $"http://{LocalIp}:{Port}";
    }

    private static string ResolveDataRoot()
    {
        var env = Environment.GetEnvironmentVariable("SWIFTSEND_ROOT");
        if (!string.IsNullOrWhiteSpace(env) && Directory.Exists(env))
            return Path.GetFullPath(env);

        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null)
        {
            if (Directory.Exists(Path.Combine(dir.FullName, "shared", "templates")))
                return dir.FullName;
            dir = dir.Parent;
        }

        // published: pastas de dados ao lado do executável
        return Path.GetFullPath(AppContext.BaseDirectory);
    }

    private static string ResolveSharedDir(string dataRoot)
    {
        var atRoot = Path.Combine(dataRoot, "shared");
        if (Directory.Exists(atRoot))
            return atRoot;

        var beside = Path.Combine(AppContext.BaseDirectory, "shared");
        return Directory.Exists(beside) ? beside : atRoot;
    }

    private static string GetLocalIp()
    {
        try
        {
            using var socket = new System.Net.Sockets.Socket(
                System.Net.Sockets.AddressFamily.InterNetwork,
                System.Net.Sockets.SocketType.Dgram,
                System.Net.Sockets.ProtocolType.Udp);
            socket.Connect("8.8.8.8", 80);
            if (socket.LocalEndPoint is System.Net.IPEndPoint ep)
                return ep.Address.ToString();
        }
        catch
        {
            // ignore
        }

        return "127.0.0.1";
    }

    public static string FormatSize(long bytes)
    {
        double size = bytes;
        string[] units = ["B", "KB", "MB", "GB", "TB"];
        foreach (var unit in units)
        {
            if (size < 1024)
                return string.Format(System.Globalization.CultureInfo.InvariantCulture, "{0:0.0} {1}", size, unit);
            size /= 1024;
        }

        return string.Format(System.Globalization.CultureInfo.InvariantCulture, "{0:0.0} PB", size);
    }
}
