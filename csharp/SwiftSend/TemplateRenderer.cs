using Fluid;

namespace SwiftSend;

internal sealed class TemplateRenderer
{
    private readonly FluidParser _parser = new();
    private readonly TemplateOptions _options = new();

    public TemplateRenderer()
    {
        _options.MemberAccessStrategy = UnsafeMemberAccessStrategy.Instance;
    }

    public async Task<string> RenderAsync(string templateName, object model)
    {
        var path = Path.Combine(AppPaths.TemplatesDir, templateName);
        if (!File.Exists(path))
            throw new FileNotFoundException($"Template não encontrado: {path}");

        var source = await File.ReadAllTextAsync(path);
        if (!_parser.TryParse(source, out var template, out var error))
            throw new InvalidOperationException($"Erro no template {templateName}: {error}");

        var context = new TemplateContext(model, _options);
        return await template.RenderAsync(context);
    }
}

internal sealed class FileEntry
{
    public string name { get; init; } = "";
    public string size { get; init; } = "";
}
