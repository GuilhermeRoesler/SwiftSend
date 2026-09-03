using Xunit;

namespace SwiftSend.Tests;

public class AppPathsTests
{
    [Theory]
    [InlineData(0, "0.0 B")]
    [InlineData(10, "10.0 B")]
    [InlineData(1023, "1023.0 B")]
    [InlineData(1024, "1.0 KB")]
    [InlineData(1536, "1.5 KB")]
    [InlineData(1048576, "1.0 MB")]
    public void FormatSize_UsesExpectedUnits(long bytes, string expected)
    {
        Assert.Equal(expected, AppPaths.FormatSize(bytes));
    }

    [Fact]
    public void Port_Is5000()
    {
        Assert.Equal(5000, AppPaths.Port);
    }

    [Fact]
    public void SharedTemplates_AreReachableFromRepo()
    {
        Assert.True(Directory.Exists(AppPaths.TemplatesDir));
        Assert.True(File.Exists(Path.Combine(AppPaths.TemplatesDir, "dashboard.html")));
        Assert.True(File.Exists(Path.Combine(AppPaths.TemplatesDir, "home.html")));
    }
}
