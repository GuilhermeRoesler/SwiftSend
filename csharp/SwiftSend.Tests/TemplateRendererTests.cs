using Xunit;

namespace SwiftSend.Tests;

public class TemplateRendererTests
{
    [Fact]
    public async Task RenderAsync_HomeTemplate_Succeeds()
    {
        var renderer = new TemplateRenderer();
        var html = await renderer.RenderAsync("home.html", new { is_desktop = false });
        Assert.Contains("Compartilhamento Local", html);
        Assert.DoesNotContain("Servidor Ativo", html);
    }

    [Fact]
    public async Task RenderAsync_DashboardTemplate_Succeeds()
    {
        var renderer = new TemplateRenderer();
        var html = await renderer.RenderAsync("dashboard.html", new
        {
            base_url = "http://192.168.0.1:5000",
            received_count = 2,
            upload_path = @"C:\tmp",
            is_desktop = true,
        });
        Assert.Contains("Servidor Ativo", html);
        Assert.Contains("http://192.168.0.1:5000", html);
    }
}
