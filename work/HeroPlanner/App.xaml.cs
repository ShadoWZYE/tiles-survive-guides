using System.Windows;
using System.Runtime.InteropServices;
using System.Threading;

namespace TilesSurviveHeroPlanner;

public partial class App : Application
{
    private Mutex? _instance;
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] private static extern IntPtr FindWindow(string? className,string title);
    [DllImport("user32.dll")] private static extern bool ShowWindow(IntPtr window,int command);
    [DllImport("user32.dll")] private static extern bool SetForegroundWindow(IntPtr window);
    protected override void OnStartup(StartupEventArgs e)
    {
        _instance=new Mutex(true,"Local\\TilesSurviveHeroPlanner.Profile",out bool first);
        if(!first){var window=FindWindow(null,"Tiles Survive Hero Planner");if(window!=IntPtr.Zero){ShowWindow(window,9);SetForegroundWindow(window);}_instance.Dispose();_instance=null;Shutdown();return;}
        base.OnStartup(e);
    }
    protected override void OnExit(ExitEventArgs e){if(_instance is not null){_instance.ReleaseMutex();_instance.Dispose();}base.OnExit(e);}
}
