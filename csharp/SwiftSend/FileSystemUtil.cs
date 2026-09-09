using System.Diagnostics;

namespace SwiftSend;

/// <summary>Helpers de FS alinhados com python/fsutil.py.</summary>
internal static class FileSystemUtil
{
    public static string? TrySanitizeFileName(string name)
    {
        var file = Path.GetFileName(name).Trim();
        if (string.IsNullOrWhiteSpace(file) || file is "." or "..")
            return null;
        foreach (var c in Path.GetInvalidFileNameChars())
            file = file.Replace(c, '_');
        return string.IsNullOrWhiteSpace(file) ? null : file;
    }

    public static string? ResolveManagedFolder(string? kind) => kind switch
    {
        "received" => AppPaths.UploadFolder,
        "public" => AppPaths.PublicFolder,
        _ => null,
    };

    public static string? SafePathInFolder(string folder, string? name)
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

    public static string UniqueDest(string folder, string filename)
    {
        var dest = Path.Combine(folder, filename);
        if (!File.Exists(dest))
            return dest;

        var stem = Path.GetFileNameWithoutExtension(filename);
        var ext = Path.GetExtension(filename);
        for (var n = 2; ; n++)
        {
            var candidate = Path.Combine(folder, $"{stem}-{n}{ext}");
            if (!File.Exists(candidate))
                return candidate;
        }
    }

    public static List<FileEntry> ListFolderFiles(string folder)
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

    public static bool WantsReplace(string? value)
    {
        var raw = (value ?? "").Trim().ToLowerInvariant();
        return raw is "1" or "true" or "yes" or "on";
    }

    public static void DefaultOpenFolder(string path)
    {
        Directory.CreateDirectory(path);
        try
        {
            Process.Start(new ProcessStartInfo
            {
                FileName = path,
                UseShellExecute = true,
            });
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"Não foi possível abrir pasta {path}: {ex.Message}");
        }
    }
}
