using System.Collections.Concurrent;
using System.Security.Cryptography;

namespace SwiftSend;

/// <summary>Tokens efêmeros para o visitante desfazer o próprio upload (~10 min).</summary>
internal static class UploadTokenStore
{
    public const int ManageSeconds = 600;

    private static readonly ConcurrentDictionary<string, UploadReceipt> Tokens = new();

    private sealed record UploadReceipt(string Name, DateTimeOffset ExpiresAt);

    private static void PurgeExpired()
    {
        var now = DateTimeOffset.UtcNow;
        foreach (var pair in Tokens)
        {
            if (pair.Value.ExpiresAt <= now)
                Tokens.TryRemove(pair.Key, out _);
        }
    }

    public static object Issue(string name)
    {
        PurgeExpired();
        foreach (var pair in Tokens)
        {
            if (string.Equals(pair.Value.Name, name, StringComparison.Ordinal))
                Tokens.TryRemove(pair.Key, out _);
        }

        var token = Convert.ToBase64String(RandomNumberGenerator.GetBytes(24))
            .TrimEnd('=')
            .Replace('+', '-')
            .Replace('/', '_');
        Tokens[token] = new UploadReceipt(name, DateTimeOffset.UtcNow.AddSeconds(ManageSeconds));
        return new { name, token, expires_in = ManageSeconds };
    }

    public static string? Consume(string token)
    {
        if (string.IsNullOrWhiteSpace(token))
            return null;

        PurgeExpired();
        return Tokens.TryRemove(token, out var receipt) ? receipt.Name : null;
    }
}
