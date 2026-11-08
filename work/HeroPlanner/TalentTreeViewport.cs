using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;

namespace TilesSurviveHeroPlanner;

/// <summary>Canvas navigation isolated from node editing and account progress.</summary>
public sealed class TalentTreeViewport : Grid
{
    private readonly Canvas _tree;
    private readonly Border _surface;
    private readonly TextBlock _label;
    private readonly ScaleTransform _scale = new();
    private readonly TranslateTransform _translate = new();
    private double _zoom = 1, _panX, _panY;
    private Point? _drag;
    public double Zoom => _zoom;
    public Point Pan => new(_panX, _panY);
    public Border Surface => _surface;

    public TalentTreeViewport(Canvas tree)
    {
        _tree = tree;
        RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        RowDefinitions.Add(new RowDefinition());
        var controls = new WrapPanel { Margin = new Thickness(0, 0, 0, 8) };
        Children.Add(controls);
        _label = new TextBlock { Foreground = Brushes.White, VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(8, 0, 12, 0) };
        void Control(string text, Action action)
        {
            var button = new Button { Content = text, Padding = new Thickness(12, 5, 12, 5), Margin = new Thickness(0, 0, 5, 0) };
            System.Windows.Automation.AutomationProperties.SetName(button, "Talent tree " + text);
            button.Click += (_, _) => action(); controls.Children.Add(button);
        }
        Control("−", () => SetZoom(_zoom / 1.25));
        Control("+", () => SetZoom(_zoom * 1.25));
        Control("Fit", Fit);
        controls.Children.Add(_label);
        controls.Children.Add(new TextBlock { Text = "Wheel to zoom · drag empty space to pan", Foreground = Brushes.LightSteelBlue, VerticalAlignment = VerticalAlignment.Center });
        _surface = new Border { ClipToBounds = true, Background = new SolidColorBrush(Color.FromRgb(19, 27, 47)), BorderBrush = new SolidColorBrush(Color.FromRgb(53, 68, 102)), BorderThickness = new Thickness(1), CornerRadius = new CornerRadius(14), Cursor = Cursors.Hand };
        SetRow(_surface, 1); Children.Add(_surface);
        var stage = new Canvas { ClipToBounds = false };
        _surface.Child = stage; stage.Children.Add(tree);
        var transforms = new TransformGroup(); transforms.Children.Add(_scale); transforms.Children.Add(_translate); tree.RenderTransform = transforms;
        _surface.SizeChanged += (_, _) => UpdateTransform();
        _surface.PreviewMouseWheel += (_, e) => { SetZoom(_zoom * (e.Delta > 0 ? 1.15 : 1 / 1.15), e.GetPosition(_surface)); e.Handled = true; };
        _surface.MouseLeftButtonDown += (_, e) =>
        {
            for (DependencyObject? node = e.OriginalSource as DependencyObject; node is not null && node != _surface; node = node is Visual ? VisualTreeHelper.GetParent(node) : LogicalTreeHelper.GetParent(node))
                if (node is Button) return;
            if (_surface.CaptureMouse()) { _drag = e.GetPosition(_surface); _surface.Cursor = Cursors.ScrollAll; e.Handled = true; }
        };
        _surface.MouseMove += (_, e) =>
        {
            if (_drag is not Point last || !_surface.IsMouseCaptured) return;
            if (e.LeftButton != MouseButtonState.Pressed) { EndDrag(); return; }
            var now = e.GetPosition(_surface); PanBy(now.X - last.X, now.Y - last.Y); _drag = now; e.Handled = true;
        };
        _surface.MouseLeftButtonUp += (_, e) => { if (_drag is not null) { EndDrag(); e.Handled = true; } };
        _surface.LostMouseCapture += (_, _) => { _drag = null; _surface.Cursor = Cursors.Hand; };
        Unloaded += (_, _) => EndDrag();
        UpdateTransform();
    }

    private double FitScale => Math.Max(.05, Math.Min(Math.Max(1, _surface.ActualWidth - 12) / 900, Math.Max(1, _surface.ActualHeight - 12) / 800));
    public void Fit() { _zoom = 1; _panX = _panY = 0; EndDrag(); UpdateTransform(); }
    public void SetZoom(double zoom, Point? anchor = null)
    {
        double old = FitScale * _zoom, next = Math.Clamp(zoom, .5, 3), scaled = FitScale * next;
        var point = anchor ?? new Point(_surface.ActualWidth / 2, _surface.ActualHeight / 2);
        double x = (point.X - _translate.X) / old, y = (point.Y - _translate.Y) / old;
        _zoom = next;
        _panX = point.X - x * scaled - (_surface.ActualWidth - 900 * scaled) / 2;
        _panY = point.Y - y * scaled - (_surface.ActualHeight - 800 * scaled) / 2;
        UpdateTransform();
    }
    public void PanBy(double x, double y) { _panX += x; _panY += y; UpdateTransform(); }
    private void EndDrag() { _drag = null; if (_surface.IsMouseCaptured) _surface.ReleaseMouseCapture(); _surface.Cursor = Cursors.Hand; }
    private void UpdateTransform()
    {
        double scale = FitScale * _zoom;
        _panX = Math.Clamp(_panX, -900 * scale / 2, 900 * scale / 2);
        _panY = Math.Clamp(_panY, -800 * scale / 2, 800 * scale / 2);
        _scale.ScaleX = _scale.ScaleY = scale;
        _translate.X = (_surface.ActualWidth - 900 * scale) / 2 + _panX;
        _translate.Y = (_surface.ActualHeight - 800 * scale) / 2 + _panY;
        _label.Text = $"{_zoom * 100:0}%";
    }
}
