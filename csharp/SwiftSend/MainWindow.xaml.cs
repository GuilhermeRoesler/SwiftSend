using System.Windows;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.Wpf;

namespace SwiftSend;

public partial class MainWindow : Window
{
    private readonly WebView2 _webView = new();

    public MainWindow()
    {
        Title = "SwiftSend - Transferência de Arquivos";
        Width = 900;
        Height = 700;
        Content = _webView;
        Loaded += OnLoaded;
    }

    private async void OnLoaded(object sender, RoutedEventArgs e)
    {
        try
        {
            await _webView.EnsureCoreWebView2Async();
            _webView.CoreWebView2.Settings.AreDefaultContextMenusEnabled = true;
            _webView.Source = new Uri($"http://127.0.0.1:{AppPaths.Port}/");
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                "Falha ao iniciar o WebView2. Instale o runtime Microsoft Edge WebView2.\n\n" + ex.Message,
                "SwiftSend",
                MessageBoxButton.OK,
                MessageBoxImage.Error);
            Close();
        }
    }
}
