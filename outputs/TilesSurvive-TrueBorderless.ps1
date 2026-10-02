$ErrorActionPreference = 'Stop'

$source = @'
using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading;

public static class TilesSurviveTrueBorderless
{
    [StructLayout(LayoutKind.Sequential)] private struct RECT { public int Left, Top, Right, Bottom; }
    [StructLayout(LayoutKind.Sequential)] private struct MONITORINFO { public int cbSize; public RECT rcMonitor; public RECT rcWork; public uint dwFlags; }
    [StructLayout(LayoutKind.Sequential)] private struct POINT { public int X, Y; }

    [DllImport("user32.dll", EntryPoint="GetWindowLongPtrW", SetLastError=true)] private static extern IntPtr GetWindowLongPtr(IntPtr hWnd, int index);
    [DllImport("user32.dll", EntryPoint="SetWindowLongPtrW", SetLastError=true)] private static extern IntPtr SetWindowLongPtr(IntPtr hWnd, int index, IntPtr value);
    [DllImport("user32.dll", SetLastError=true)] private static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
    [DllImport("user32.dll")] private static extern IntPtr MonitorFromWindow(IntPtr hWnd, uint flags);
    [DllImport("user32.dll", SetLastError=true)] private static extern bool GetMonitorInfo(IntPtr monitor, ref MONITORINFO info);
    [DllImport("user32.dll", SetLastError=true)] private static extern bool SetWindowPos(IntPtr hWnd, IntPtr after, int x, int y, int width, int height, uint flags);
    [DllImport("user32.dll")] private static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] private static extern bool IsWindow(IntPtr hWnd);
    [DllImport("user32.dll")] private static extern short GetAsyncKeyState(int key);
    [DllImport("user32.dll", SetLastError=true)] private static extern bool GetClientRect(IntPtr hWnd, out RECT rect);
    [DllImport("user32.dll", SetLastError=true)] private static extern bool ClientToScreen(IntPtr hWnd, ref POINT point);
    [DllImport("user32.dll")] private static extern bool GetCursorPos(out POINT point);
    [DllImport("user32.dll")] private static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] private static extern void mouse_event(uint flags, uint dx, uint dy, uint data, UIntPtr extraInfo);

    private static readonly IntPtr HWND_TOPMOST = new IntPtr(-1);
    private static readonly IntPtr HWND_NOTOPMOST = new IntPtr(-2);
    private const int GWL_STYLE = -16, GWL_EXSTYLE = -20;
    private const int VK_CONTROL = 0x11, VK_SHIFT = 0x10, VK_ESCAPE = 0x1B, VK_M = 0x4D, VK_F11 = 0x7A;
    private const uint MOUSEEVENTF_LEFTDOWN = 0x0002, MOUSEEVENTF_LEFTUP = 0x0004;
    private const uint MONITOR_DEFAULTTONEAREST = 2;
    private const uint APPLY_FLAGS = 0x0200 | 0x0020 | 0x0040;
    private const uint Z_ONLY_FLAGS = 0x0001 | 0x0002 | 0x0010 | 0x0200;
    private const long BORDER_MASK = 0x00C00000L | 0x00040000L | 0x00080000L | 0x00020000L | 0x00010000L;
    private const long EX_BORDER_MASK = 0x00000001L | 0x00000100L | 0x00000200L | 0x00020000L;
    private static readonly string LogPath = Path.Combine(Path.GetTempPath(), "TilesSurvive-TrueBorderless.log");

    private static void Log(string text)
    {
        File.AppendAllText(LogPath, DateTime.Now.ToString("s") + " " + text + Environment.NewLine);
    }

    private static IntPtr WaitForGameWindow()
    {
        DateTime deadline = DateTime.UtcNow.AddMinutes(2);
        while (DateTime.UtcNow < deadline)
        {
            foreach (Process process in Process.GetProcessesByName("tspc"))
            {
                process.Refresh();
                if (process.MainWindowHandle != IntPtr.Zero) return process.MainWindowHandle;
            }
            Thread.Sleep(500);
        }
        return IntPtr.Zero;
    }

    private static bool KeyDown(int key)
    {
        return (GetAsyncKeyState(key) & 0x8000) != 0;
    }

    private static void ClickBackButton(IntPtr window)
    {
        RECT client;
        if (!GetClientRect(window, out client))
            throw new InvalidOperationException("GetClientRect failed: " + Marshal.GetLastWin32Error());

        int clickX = Math.Max(24, (client.Right / 2) - 380);
        int clickY = Math.Max(24, client.Bottom - 62);
        POINT click = new POINT { X = clickX, Y = clickY };
        if (!ClientToScreen(window, ref click))
            throw new InvalidOperationException("ClientToScreen failed: " + Marshal.GetLastWin32Error());

        POINT previous;
        GetCursorPos(out previous);
        SetCursorPos(click.X, click.Y);
        Thread.Sleep(40);
        mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, UIntPtr.Zero);
        Thread.Sleep(30);
        mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, UIntPtr.Zero);
        Thread.Sleep(80);
        SetCursorPos(previous.X, previous.Y);
        Log("Escape clicked the back control at client position " + clickX + "," + clickY + ".");
    }

    private static void ClickMapButton(IntPtr window)
    {
        RECT client;
        if (!GetClientRect(window, out client))
            throw new InvalidOperationException("GetClientRect failed: " + Marshal.GetLastWin32Error());

        int clickX = Math.Max(24, client.Right - 46);
        int clickY = Math.Max(24, client.Bottom - 50);
        POINT click = new POINT { X = clickX, Y = clickY };
        if (!ClientToScreen(window, ref click))
            throw new InvalidOperationException("ClientToScreen failed: " + Marshal.GetLastWin32Error());

        POINT previous;
        GetCursorPos(out previous);
        SetCursorPos(click.X, click.Y);
        Thread.Sleep(40);
        mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, UIntPtr.Zero);
        Thread.Sleep(30);
        mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, UIntPtr.Zero);
        Thread.Sleep(80);
        SetCursorPos(previous.X, previous.Y);
        Log("M clicked the map/settlement control at client position " + clickX + "," + clickY + ".");
    }

    public static void Run()
    {
        using (Mutex mutex = new Mutex(false, "Local\\TilesSurviveTrueBorderless"))
        {
            if (!mutex.WaitOne(0)) return;

            IntPtr window = IntPtr.Zero;
            IntPtr originalStyle = IntPtr.Zero;
            IntPtr originalExStyle = IntPtr.Zero;
            RECT originalRect = new RECT();
            bool changed = false;
            bool topmost = false;

            try
            {
                Log("Waiting for an authenticated TilesSurvive window.");
                window = WaitForGameWindow();
                if (window == IntPtr.Zero) throw new InvalidOperationException("No TilesSurvive window appeared within two minutes.");
                if (!GetWindowRect(window, out originalRect)) throw new InvalidOperationException("GetWindowRect failed: " + Marshal.GetLastWin32Error());

                originalStyle = GetWindowLongPtr(window, GWL_STYLE);
                originalExStyle = GetWindowLongPtr(window, GWL_EXSTYLE);
                SetWindowLongPtr(window, GWL_STYLE, new IntPtr(originalStyle.ToInt64() & ~BORDER_MASK));
                SetWindowLongPtr(window, GWL_EXSTYLE, new IntPtr(originalExStyle.ToInt64() & ~EX_BORDER_MASK));

                IntPtr monitor = MonitorFromWindow(window, MONITOR_DEFAULTTONEAREST);
                MONITORINFO info = new MONITORINFO { cbSize = Marshal.SizeOf(typeof(MONITORINFO)) };
                if (!GetMonitorInfo(monitor, ref info)) throw new InvalidOperationException("GetMonitorInfo failed: " + Marshal.GetLastWin32Error());
                RECT full = info.rcMonitor;
                int width = full.Right - full.Left, height = full.Bottom - full.Top;
                if (!SetWindowPos(window, HWND_TOPMOST, full.Left, full.Top, width, height, APPLY_FLAGS))
                    throw new InvalidOperationException("SetWindowPos failed: " + Marshal.GetLastWin32Error());

                changed = true;
                topmost = true;
                Log("True borderless mode enabled at " + width + "x" + height + ".");

                bool exitWasDown = false;
                bool escapeArmed = true;
                int escapeReleasedTicks = 0;
                bool mapArmed = true;
                int mapReleasedTicks = 0;
                while (IsWindow(window))
                {
                    bool gameFocused = GetForegroundWindow() == window;
                    if (gameFocused && !topmost)
                    {
                        SetWindowPos(window, HWND_TOPMOST, 0, 0, 0, 0, Z_ONLY_FLAGS);
                        topmost = true;
                    }
                    else if (!gameFocused && topmost)
                    {
                        SetWindowPos(window, HWND_NOTOPMOST, 0, 0, 0, 0, Z_ONLY_FLAGS);
                        topmost = false;
                    }

                    bool exitIsDown = KeyDown(VK_CONTROL) && KeyDown(VK_SHIFT) && KeyDown(VK_F11);
                    if (exitIsDown && !exitWasDown) break;
                    exitWasDown = exitIsDown;

                    bool escapeIsDown = KeyDown(VK_ESCAPE);
                    if (escapeIsDown)
                    {
                        escapeReleasedTicks = 0;
                        if (gameFocused && escapeArmed)
                        {
                            escapeArmed = false;
                            try { ClickBackButton(window); }
                            catch (Exception error) { Log("Escape mapping failed: " + error.Message); }
                        }
                    }
                    else if (!escapeArmed)
                    {
                        escapeReleasedTicks++;
                        if (escapeReleasedTicks >= 5)
                        {
                            escapeArmed = true;
                            escapeReleasedTicks = 0;
                        }
                    }

                    bool mapIsDown = KeyDown(VK_M);
                    if (mapIsDown)
                    {
                        mapReleasedTicks = 0;
                        if (gameFocused && mapArmed)
                        {
                            mapArmed = false;
                            try { ClickMapButton(window); }
                            catch (Exception error) { Log("M mapping failed: " + error.Message); }
                        }
                    }
                    else if (!mapArmed)
                    {
                        mapReleasedTicks++;
                        if (mapReleasedTicks >= 5)
                        {
                            mapArmed = true;
                            mapReleasedTicks = 0;
                        }
                    }
                    Thread.Sleep(20);
                }
            }
            catch (Exception error)
            {
                Log("Helper error: " + error.Message);
                throw;
            }
            finally
            {
                if (changed && window != IntPtr.Zero && IsWindow(window))
                {
                    SetWindowPos(window, HWND_NOTOPMOST, 0, 0, 0, 0, Z_ONLY_FLAGS);
                    SetWindowLongPtr(window, GWL_STYLE, originalStyle);
                    SetWindowLongPtr(window, GWL_EXSTYLE, originalExStyle);
                    SetWindowPos(window, IntPtr.Zero, originalRect.Left, originalRect.Top,
                        originalRect.Right - originalRect.Left, originalRect.Bottom - originalRect.Top, APPLY_FLAGS);
                    Log("Original window restored.");
                }
                mutex.ReleaseMutex();
            }
        }
    }
}
'@

Add-Type -TypeDefinition $source -Language CSharp
[TilesSurviveTrueBorderless]::Run()
