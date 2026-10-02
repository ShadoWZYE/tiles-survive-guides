param([switch]$ToggleOnce)

$ErrorActionPreference = 'Stop'

$source = @'
using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading;

public static class TilesSurviveHotkey
{
    [StructLayout(LayoutKind.Sequential)] private struct RECT { public int Left, Top, Right, Bottom; }
    [StructLayout(LayoutKind.Sequential)] private struct MONITORINFO { public int cbSize; public RECT rcMonitor; public RECT rcWork; public uint dwFlags; }
    [StructLayout(LayoutKind.Sequential)] private struct POINT { public int X, Y; }
    [StructLayout(LayoutKind.Sequential)] private struct MSG { public IntPtr hwnd; public uint message; public UIntPtr wParam; public IntPtr lParam; public uint time; public POINT pt; public uint lPrivate; }

    [DllImport("user32.dll", SetLastError=true)] private static extern bool RegisterHotKey(IntPtr hWnd, int id, uint modifiers, uint key);
    [DllImport("user32.dll", SetLastError=true)] private static extern bool UnregisterHotKey(IntPtr hWnd, int id);
    [DllImport("user32.dll", SetLastError=true)] private static extern int GetMessage(out MSG message, IntPtr hWnd, uint min, uint max);
    [DllImport("user32.dll", EntryPoint="GetWindowLongPtrW", SetLastError=true)] private static extern IntPtr GetWindowLongPtr(IntPtr hWnd, int index);
    [DllImport("user32.dll", EntryPoint="SetWindowLongPtrW", SetLastError=true)] private static extern IntPtr SetWindowLongPtr(IntPtr hWnd, int index, IntPtr value);
    [DllImport("user32.dll", SetLastError=true)] private static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
    [DllImport("user32.dll")] private static extern IntPtr MonitorFromWindow(IntPtr hWnd, uint flags);
    [DllImport("user32.dll", SetLastError=true)] private static extern bool GetMonitorInfo(IntPtr monitor, ref MONITORINFO info);
    [DllImport("user32.dll", SetLastError=true)] private static extern bool SetWindowPos(IntPtr hWnd, IntPtr after, int x, int y, int width, int height, uint flags);

    private const uint WM_HOTKEY = 0x0312, VK_F11 = 0x7A, MOD_CONTROL = 0x0002, MOD_SHIFT = 0x0004, MOD_NOREPEAT = 0x4000;
    private const int GWL_STYLE = -16, GWL_EXSTYLE = -20;
    private const uint MONITOR_DEFAULTTONEAREST = 2, FRAME_FLAGS = 0x0004 | 0x0200 | 0x0020 | 0x0040;
    private const long BORDER_MASK = 0x00C00000L | 0x00040000L | 0x00080000L | 0x00020000L | 0x00010000L;
    private const long EX_BORDER_MASK = 0x00000001L | 0x00000100L | 0x00000200L | 0x00020000L;
    private static readonly string LogPath = Path.Combine(Path.GetTempPath(), "TilesSurvive-F11.log");
    private static IntPtr window, originalStyle, originalExStyle;
    private static RECT originalRect;
    private static bool borderless;

    private static void Log(string text) { File.AppendAllText(LogPath, DateTime.Now.ToString("s") + " " + text + Environment.NewLine); }

    private static IntPtr FindGameWindow()
    {
        foreach (Process process in Process.GetProcessesByName("tspc"))
        {
            process.Refresh();
            if (process.MainWindowHandle != IntPtr.Zero) return process.MainWindowHandle;
        }
        return IntPtr.Zero;
    }

    private static void Restore()
    {
        if (!borderless || window == IntPtr.Zero) return;
        SetWindowLongPtr(window, GWL_STYLE, originalStyle);
        SetWindowLongPtr(window, GWL_EXSTYLE, originalExStyle);
        SetWindowPos(window, IntPtr.Zero, originalRect.Left, originalRect.Top,
            originalRect.Right - originalRect.Left, originalRect.Bottom - originalRect.Top, FRAME_FLAGS);
        borderless = false;
        Log("Restored the original game window.");
    }

    private static void Toggle()
    {
        IntPtr current = FindGameWindow();
        if (current == IntPtr.Zero) { Log("F11 received, but no TilesSurvive window was found."); return; }
        if (window != current) { window = current; borderless = false; }
        if (borderless) { Restore(); return; }
        if (!GetWindowRect(window, out originalRect)) throw new InvalidOperationException("GetWindowRect failed: " + Marshal.GetLastWin32Error());

        IntPtr monitor = MonitorFromWindow(window, MONITOR_DEFAULTTONEAREST);
        MONITORINFO info = new MONITORINFO { cbSize = Marshal.SizeOf(typeof(MONITORINFO)) };
        if (!GetMonitorInfo(monitor, ref info)) throw new InvalidOperationException("GetMonitorInfo failed: " + Marshal.GetLastWin32Error());

        originalStyle = GetWindowLongPtr(window, GWL_STYLE);
        originalExStyle = GetWindowLongPtr(window, GWL_EXSTYLE);
        SetWindowLongPtr(window, GWL_STYLE, new IntPtr(originalStyle.ToInt64() & ~BORDER_MASK));
        SetWindowLongPtr(window, GWL_EXSTYLE, new IntPtr(originalExStyle.ToInt64() & ~EX_BORDER_MASK));
        RECT work = info.rcWork;
        int workWidth = work.Right - work.Left, workHeight = work.Bottom - work.Top;
        int scale = Math.Min(workWidth / 16, workHeight / 9);
        int width = scale * 16, height = scale * 9;
        int x = work.Left + (workWidth - width) / 2;
        int y = work.Top + (workHeight - height) / 2;
        if (!SetWindowPos(window, IntPtr.Zero, x, y, width, height, FRAME_FLAGS))
            throw new InvalidOperationException("SetWindowPos failed: " + Marshal.GetLastWin32Error());
        borderless = true;
        Log("16:9 borderless mode enabled at " + width + "x" + height + ".");
    }

    public static void ToggleOnce()
    {
        try { Toggle(); }
        catch (Exception error) { Log("Direct toggle failed: " + error.Message); throw; }
    }

    public static void Run()
    {
        using (Mutex mutex = new Mutex(false, "Local\\TilesSurviveF11Helper"))
        {
            if (!mutex.WaitOne(0)) return;
            bool f11Registered = false, exitRegistered = false;
            try
            {
                f11Registered = RegisterHotKey(IntPtr.Zero, 1, MOD_NOREPEAT, VK_F11);
                if (!f11Registered) throw new InvalidOperationException("Could not register F11: " + Marshal.GetLastWin32Error());
                exitRegistered = RegisterHotKey(IntPtr.Zero, 2, MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, VK_F11);
                if (!exitRegistered) throw new InvalidOperationException("Could not register Ctrl+Shift+F11: " + Marshal.GetLastWin32Error());
                Log("Native helper started. F11 toggles borderless mode; Ctrl+Shift+F11 exits.");

                MSG message;
                while (true)
                {
                    int result = GetMessage(out message, IntPtr.Zero, 0, 0);
                    if (result == -1) throw new InvalidOperationException("GetMessage failed: " + Marshal.GetLastWin32Error());
                    if (result == 0) break;
                    if (message.message != WM_HOTKEY) continue;
                    ulong id = message.wParam.ToUInt64();
                    if (id == 2) { Restore(); break; }
                    if (id == 1) { try { Toggle(); } catch (Exception error) { Log("Toggle failed: " + error.Message); } }
                }
            }
            catch (Exception error) { Log("Helper stopped with error: " + error.Message); throw; }
            finally
            {
                Restore();
                if (f11Registered) UnregisterHotKey(IntPtr.Zero, 1);
                if (exitRegistered) UnregisterHotKey(IntPtr.Zero, 2);
                mutex.ReleaseMutex();
            }
        }
    }
}
'@

Add-Type -TypeDefinition $source -Language CSharp
if ($ToggleOnce) {
    [TilesSurviveHotkey]::ToggleOnce()
} else {
    [TilesSurviveHotkey]::Run()
}
