using System.Windows;
using System.Runtime.InteropServices;
using System.Threading;

namespace TilesSurviveHeroPlanner;

public partial class App : Application
{
    public bool IsolatedTestWindows {get;set;}
    private Mutex? _instance;
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] private static extern IntPtr FindWindow(string? className,string title);
    [DllImport("user32.dll")] private static extern bool ShowWindow(IntPtr window,int command);
    [DllImport("user32.dll")] private static extern bool SetForegroundWindow(IntPtr window);
    protected override void OnStartup(StartupEventArgs e)
    {
        if(IsolatedTestWindows)return;
        _instance=new Mutex(true,"Local\\TilesSurviveHeroPlanner.Profile",out bool first);
        if(!first){var window=FindWindow(null,"Tiles Survive Hero Planner");if(window!=IntPtr.Zero){ShowWindow(window,9);SetForegroundWindow(window);}_instance.Dispose();_instance=null;Shutdown();return;}
        base.OnStartup(e);
        var main=new MainWindow(); MainWindow=main; main.Show();
        var handle=new System.Windows.Interop.WindowInteropHelper(main).Handle;
        ShowWindow(handle,9); main.Activate(); SetForegroundWindow(handle);
    }
    protected override void OnExit(ExitEventArgs e){if(_instance is not null){_instance.ReleaseMutex();_instance.Dispose();}base.OnExit(e);}
}
