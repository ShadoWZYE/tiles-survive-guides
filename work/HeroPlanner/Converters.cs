using System.Globalization;
using System.Windows;
using System.Windows.Data;
using System.Windows.Media;

namespace TilesSurviveHeroPlanner;

public sealed class RarityBrushConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture) =>
        value?.ToString() switch
        {
            "SSR" => new SolidColorBrush(Color.FromRgb(255, 158, 60)),
            "SR" => new SolidColorBrush(Color.FromRgb(196, 91, 235)),
            "R" => new SolidColorBrush(Color.FromRgb(72, 173, 244)),
            _ => new SolidColorBrush(Color.FromRgb(81, 112, 151)),
        };

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture) =>
        throw new NotSupportedException();
}

public sealed class BoolVisibilityConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture) =>
        value is true ? Visibility.Visible : Visibility.Collapsed;

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture) =>
        throw new NotSupportedException();
}

public sealed class NumberConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture) =>
        value is double number ? number.ToString("N0") : value?.ToString() ?? "";

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture) =>
        throw new NotSupportedException();
}
