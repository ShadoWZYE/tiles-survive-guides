using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace TilesSurviveHeroPlanner;

public partial class MainWindow
{
    private FrameworkElement CreateBehemothStarEditor(string key, ArmyContextEntry entry, int current, out Slider result)
    {
        var panel = new StackPanel();
        var preview = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(0, 10, 0, 3) }; panel.Children.Add(preview);
        var label = CopyText(""); panel.Children.Add(label);
        var slider = new Slider { Minimum = 0, Maximum = entry.Stars.Last().Level, Value = current, TickFrequency = 1, IsSnapToTickEnabled = true, Margin = new Thickness(0, 6, 0, 6), ToolTip = "Drag to the star progress; arrow keys move one step. Leftmost = unknown." }; panel.Children.Add(slider);
        System.Windows.Automation.AutomationProperties.SetName(slider, "Behemoth " + key + " star");
        var controls = new WrapPanel(); panel.Children.Add(controls);
        var color = new ComboBox { Width = 150 }; color.Items.Add(new ComboBoxItem { Content = "Unknown", Tag = 0 });
        for (int i = 1; i <= (int)Math.Ceiling(slider.Maximum / 30); i++) color.Items.Add(new ComboBoxItem { Content = BehemothStarProgress.Color(i), Tag = i });
        var star = new ComboBox { Width = 90 }; var step = new ComboBox { Width = 130 };
        for (int i = 1; i <= 5; i++) star.Items.Add(new ComboBoxItem { Content = "Star " + i, Tag = i });
        for (int i = 1; i <= 6; i++) step.Items.Add(new ComboBoxItem { Content = i + "/6" + (i == 6 ? " · full star" : ""), Tag = i });
        Field(controls, "Star colour", color); Field(controls, "Star", star); Field(controls, "Progress", step);
        var clear = new Button { Content = "Clear stars", Padding = new Thickness(9, 5, 9, 5), HorizontalAlignment = HorizontalAlignment.Left }; panel.Children.Add(clear); clear.Click += (_, _) => slider.Value = 0;
        bool syncing = false;
        void Draw()
        {
            syncing = true; int count = (int)slider.Value;
            color.SelectedIndex = count == 0 ? 0 : (count - 1) / 30 + 1;
            star.SelectedIndex = count == 0 ? 0 : (count - 1) % 30 / 6;
            step.SelectedIndex = count == 0 ? 0 : (count - 1) % 6;
            star.IsEnabled = step.IsEnabled = count > 0;
            label.Text = BehemothStarProgress.Label(count); preview.Children.Clear();
            BitmapImage Sprite(int n) => new(new Uri($"pack://application:,,,/TilesSurviveHeroPlanner;component/Images/ContextIcons/sp_base_titan_star_{n}.png"));
            foreach (var slot in BehemothStarProgress.Slots(count, _armyContextData.BehemothStarDisplay.Tiers))
            {
                var grid = new Grid { Width = 36, Height = 36, Margin = new Thickness(0, 0, 5, 0), Opacity = count == 0 ? .35 : 1 }; grid.Children.Add(new Image { Source = Sprite(slot.Base) });
                if (slot.Steps > 0)
                {
                    var image = new Image { Source = Sprite(slot.Overlay) };
                    if (slot.Steps < 6)
                    {
                        var points = new List<Point> { new(18, 18) }; for (int i = 0; i <= slot.Steps * 12; i++) { double angle = (0 - i * 5) * Math.PI / 180; points.Add(new(18 + 32 * Math.Cos(angle), 18 + 32 * Math.Sin(angle))); }
                        var figure = new PathFigure { StartPoint = points[0], IsClosed = true }; figure.Segments.Add(new PolyLineSegment(points.Skip(1), true)); image.Clip = new PathGeometry([figure]);
                    }
                    grid.Children.Add(image);
                }
                preview.Children.Add(grid);
            }
            syncing = false;
        }
        void Choose() { if (!syncing && color.SelectedItem is ComboBoxItem c) slider.Value = (int)c.Tag == 0 ? 0 : ((int)c.Tag - 1) * 30 + star.SelectedIndex * 6 + step.SelectedIndex + 1; }
        color.SelectionChanged += (_, _) => Choose(); star.SelectionChanged += (_, _) => Choose(); step.SelectionChanged += (_, _) => Choose();
        slider.ValueChanged += (_, _) => Draw(); Draw(); result = slider; return panel;
    }
}
