using System.Windows;
using Microsoft.AspNetCore.Builder;

namespace SwiftSend;

public partial class App : Application
{
    private WebApplication? _webApp;
    private CancellationTokenSource? _cts;

    protected override async void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        try
        {
            _cts = new CancellationTokenSource();
            _webApp = WebServer.Build();
            await _webApp.StartAsync(_cts.Token);
            await WaitForServerAsync();

            var window = new MainWindow();
            window.Show();
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                "Não foi possível iniciar o SwiftSend.\n\n" + ex.Message,
                "SwiftSend",
                MessageBoxButton.OK,
                MessageBoxImage.Error);
            Shutdown(1);
        }
    }

    protected override async void OnExit(ExitEventArgs e)
    {
        try
        {
            _cts?.Cancel();
            if (_webApp is not null)
            {
                using var stopCts = new CancellationTokenSource(TimeSpan.FromSeconds(2));
                await _webApp.StopAsync(stopCts.Token);
                await _webApp.DisposeAsync();
            }
        }
        catch
        {
            // ignore shutdown races
        }

        base.OnExit(e);
    }

    private static async Task WaitForServerAsync()
    {
        using var client = new HttpClient { Timeout = TimeSpan.FromMilliseconds(500) };
        for (var i = 0; i < 40; i++)
        {
            try
            {
                using var response = await client.GetAsync($"http://127.0.0.1:{AppPaths.Port}/");
                if (response.IsSuccessStatusCode)
                    return;
            }
            catch
            {
                // still starting
            }

            await Task.Delay(100);
        }
    }
}
