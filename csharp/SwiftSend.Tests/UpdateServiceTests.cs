using Xunit;

namespace SwiftSend.Tests;

public sealed class UpdateServiceTests
{
    [Theory]
    [InlineData("v1.2.3", 1, 2, 3)]
    [InlineData("1.0.0", 1, 0, 0)]
    [InlineData("2.0.0-rc.1", 2, 0, 0)]
    public void NormalizeVersion_ParsesCore(string tag, int major, int minor, int patch)
    {
        var v = UpdateService.NormalizeVersion(tag);
        Assert.Equal((major, minor, patch), v);
    }

    [Theory]
    [InlineData("v1.0.1", "1.0.0", true)]
    [InlineData("1.0.0", "1.0.0", false)]
    [InlineData("v0.9.9", "1.0.0", false)]
    public void IsNewer_ComparesSemverCore(string latest, string current, bool expected)
    {
        Assert.Equal(expected, UpdateService.IsNewer(latest, current));
    }
}
