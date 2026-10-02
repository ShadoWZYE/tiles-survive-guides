using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading;

internal static class Program
{
    [StructLayout(LayoutKind.Sequential)]
    private struct Rect { public int Left, Top, Right, Bottom; }

    [StructLayout(LayoutKind.Sequential)]
    private struct MonitorInfo { public int Size; public Rect Monitor; public Rect Work; public uint Flags; }

    [StructLayout(LayoutKind.Sequential)]
    private struct Point { public int X, Y; }

    [DllImport("user32.dll", EntryPoint = "GetWindowLongPtrW", SetLastError = true)]
    private static extern IntPtr GetWindowLongPtr(IntPtr window, int index);

    [DllImport("user32.dll", EntryPoint = "SetWindowLongPtrW", SetLastError = true)]
    private static extern IntPtr SetWindowLongPtr(IntPtr window, int index, IntPtr value);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool GetWindowRect(IntPtr window, out Rect rect);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool GetClientRect(IntPtr window, out Rect rect);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool ClientToScreen(IntPtr window, ref Point point);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool ScreenToClient(IntPtr window, ref Point point);

    [DllImport("user32.dll")]
    private static extern IntPtr MonitorFromWindow(IntPtr window, uint flags);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool GetMonitorInfo(IntPtr monitor, ref MonitorInfo info);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool SetWindowPos(IntPtr window, IntPtr after, int x, int y, int width, int height, uint flags);

    [DllImport("user32.dll")]
    private static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(IntPtr window, out uint processId);

    [DllImport("user32.dll")]
    private static extern bool IsWindow(IntPtr window);

    [DllImport("user32.dll")]
    private static extern bool IsWindowVisible(IntPtr window);

    [DllImport("user32.dll")]
    private static extern bool IsIconic(IntPtr window);

    [DllImport("user32.dll")]
    private static extern bool ShowWindowAsync(IntPtr window, int command);

    [DllImport("user32.dll")]
    private static extern short GetAsyncKeyState(int key);

    [DllImport("user32.dll")]
    private static extern bool GetCursorPos(out Point point);

    [DllImport("user32.dll")]
    private static extern bool SetCursorPos(int x, int y);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool GetClipCursor(out Rect rect);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool ClipCursor(ref Rect rect);

    [DllImport("user32.dll")]
    private static extern void mouse_event(uint flags, uint dx, uint dy, uint data, UIntPtr extraInfo);

    private static readonly IntPtr Topmost = new(-1);
    private static readonly IntPtr NotTopmost = new(-2);
    private const int StyleIndex = -16;
    private const int ExtendedStyleIndex = -20;
    private const int ControlKey = 0x11;
    private const int ShiftKey = 0x10;
    private const int LeftMouseButton = 0x01;
    private const int EnterKey = 0x0D;
    private const int EscapeKey = 0x1B;
    private const int MKey = 0x4D;
    private const int F11Key = 0x7A;
    private const int RestoreWindow = 9;
    private const uint MonitorNearest = 2;
    // SWP_NOACTIVATE is essential: maintenance sizing must never steal or drop focus.
    private const uint ApplyFlags = 0x0200 | 0x0020 | 0x0040 | 0x0010;
    private const uint ZOnlyFlags = 0x0001 | 0x0002 | 0x0010 | 0x0200;
    private const uint LeftDown = 0x0002;
    private const uint LeftUp = 0x0004;
    private const long BorderMask = 0x00C00000L | 0x00040000L | 0x00080000L | 0x00020000L | 0x00010000L;
    private const long ExtendedBorderMask = 0x00000001L | 0x00000100L | 0x00000200L | 0x00020000L;
    private static readonly string LogPath = Path.Combine(Path.GetTempPath(), "TilesSurviveHelper.log");

    [STAThread]
    private static void Main()
    {
        using var mutex = new Mutex(false, "Local\\TilesSurvivePackagedHelper");
        if (!mutex.WaitOne(0)) return;

        Log("Helper started; it will follow Tiles Survive across client restarts.");
        while (true)
        {
            Log("Waiting for an authenticated TilesSurvive window.");
            var window = WaitForGameWindow();
            try
            {
                if (RunWindow(window)) break;
            }
            catch (Exception error)
            {
                Log("Window session error: " + error.Message);
            }
            Log("TilesSurvive window closed; waiting for the replacement client.");
        }
        mutex.ReleaseMutex();
    }

    private static bool RunWindow(IntPtr window)
    {
        IntPtr originalStyle = IntPtr.Zero;
        IntPtr originalExtendedStyle = IntPtr.Zero;
        var originalRect = new Rect();
        var changed = false;
        var topmost = false;

        try
        {
            if (!GetWindowRect(window, out originalRect)) ThrowWin32("GetWindowRect");

            originalStyle = GetWindowLongPtr(window, StyleIndex);
            originalExtendedStyle = GetWindowLongPtr(window, ExtendedStyleIndex);
            SetWindowLongPtr(window, StyleIndex, new IntPtr(originalStyle.ToInt64() & ~BorderMask));
            SetWindowLongPtr(window, ExtendedStyleIndex, new IntPtr(originalExtendedStyle.ToInt64() & ~ExtendedBorderMask));

            var monitor = MonitorFromWindow(window, MonitorNearest);
            var monitorInfo = new MonitorInfo { Size = Marshal.SizeOf<MonitorInfo>() };
            if (!GetMonitorInfo(monitor, ref monitorInfo)) ThrowWin32("GetMonitorInfo");

            var full = monitorInfo.Monitor;
            var width = full.Right - full.Left;
            var height = full.Bottom - full.Top;
            ApplyBorderlessBounds(window, Topmost, full, forceResizePulse: true);
            changed = true;
            topmost = true;
            Log($"True borderless mode enabled at {width}x{height}.");

            var escape = new KeyLatch();
            var map = new KeyLatch();
            var enter = new KeyLatch();
            var exitWasDown = false;
            var mouseWasDown = false;
            var chatMode = false;
            var geometryCheck = 0;

            while (IsWindow(window))
            {
                var gameFocused = IsGameProcessFocused(window);
                if (gameFocused && !topmost)
                {
                    SetWindowPos(window, Topmost, 0, 0, 0, 0, ZOnlyFlags);
                    topmost = true;
                }
                else if (!gameFocused && topmost)
                {
                    SetWindowPos(window, NotTopmost, 0, 0, 0, 0, ZOnlyFlags);
                    topmost = false;
                }

                // The client sometimes reapplies its saved window bounds after loading or
                // changing scenes. Check periodically and correct only actual drift so this
                // does not continuously disturb input or redraw the window.
                if (++geometryCheck >= 13)
                {
                    geometryCheck = 0;
                    EnsureBorderlessBounds(window, gameFocused ? Topmost : NotTopmost);
                }

                var exitIsDown = KeyDown(ControlKey) && KeyDown(ShiftKey) && KeyDown(F11Key);
                if (exitIsDown && !exitWasDown) return true;
                exitWasDown = exitIsDown;

                var mouseIsDown = KeyDown(LeftMouseButton);
                if (gameFocused && mouseIsDown && !mouseWasDown)
                {
                    if (chatMode && IsChatBackClick(window))
                    {
                        chatMode = false;
                        Log("Chat mode disabled by the chat back button.");
                    }
                    else if (!chatMode && (IsChatActivationClick(window) || IsChatInputClick(window)))
                    {
                        chatMode = true;
                        Log("Chat mode enabled by a chat or input-field click.");
                    }
                }
                mouseWasDown = mouseIsDown;

                if (enter.Triggered(KeyDown(EnterKey), gameFocused))
                {
                    if (!chatMode)
                    {
                        chatMode = true;
                        Log("Chat mode enabled by Enter.");
                    }
                }

                if (escape.Triggered(KeyDown(EscapeKey), gameFocused))
                {
                    if (chatMode)
                    {
                        chatMode = false;
                        Log("Chat mode disabled by Escape; back shortcut suppressed.");
                    }
                    else
                    {
                        ClickGameControl(window, ControlTarget.Back);
                    }
                }

                if (map.Triggered(KeyDown(MKey), gameFocused && !chatMode))
                    ClickGameControl(window, ControlTarget.Map);

                Thread.Sleep(20);
            }
        }
        catch (Exception error)
        {
            Log("Helper error: " + error.Message);
            return false;
        }
        finally
        {
            if (changed && window != IntPtr.Zero && IsWindow(window))
            {
                SetWindowPos(window, NotTopmost, 0, 0, 0, 0, ZOnlyFlags);
                SetWindowLongPtr(window, StyleIndex, originalStyle);
                SetWindowLongPtr(window, ExtendedStyleIndex, originalExtendedStyle);
                SetWindowPos(window, IntPtr.Zero, originalRect.Left, originalRect.Top,
                    originalRect.Right - originalRect.Left, originalRect.Bottom - originalRect.Top, ApplyFlags);
                Log("Original window restored.");
            }
        }
        return false;
    }

    private static IntPtr WaitForGameWindow()
    {
        IntPtr stableWindow = IntPtr.Zero;
        var stableChecks = 0;

        while (true)
        {
            foreach (var process in Process.GetProcessesByName("tspc"))
            {
                process.Refresh();
                var candidate = process.MainWindowHandle;
                if (candidate == IntPtr.Zero || !IsWindow(candidate) || !IsWindowVisible(candidate))
                    continue;

                // The official launcher can create the real game window minimized. A
                // minimized HWND reports a 0x0 client area and lives at -32000,-32000;
                // SetWindowPos cannot establish useful fullscreen bounds in that state.
                if (IsIconic(candidate))
                {
                    ShowWindowAsync(candidate, RestoreWindow);
                    stableWindow = IntPtr.Zero;
                    stableChecks = 0;
                    continue;
                }

                if (!GetClientRect(candidate, out var client) ||
                    client.Right - client.Left < 640 || client.Bottom - client.Top < 360)
                    continue;

                if (candidate != stableWindow)
                {
                    stableWindow = candidate;
                    stableChecks = 1;
                    continue;
                }

                // Require the same drawable HWND for one second. This avoids binding to
                // a transient launcher/authentication surface during a client reboot.
                if (++stableChecks >= 3)
                {
                    Log($"Bound to stable TilesSurvive window 0x{candidate.ToInt64():X} " +
                        $"for process {process.Id}; client {client.Right - client.Left}x{client.Bottom - client.Top}.");
                    return candidate;
                }
            }
            Thread.Sleep(500);
        }
    }

    private static void EnsureBorderlessBounds(IntPtr window, IntPtr zOrder)
    {
        // A minimized window has deliberately invalid screen geometry. Leave it alone;
        // the first check after the user restores it will reapply borderless bounds.
        if (IsIconic(window)) return;

        var styleChanged = false;
        var currentStyle = GetWindowLongPtr(window, StyleIndex);
        var currentExtendedStyle = GetWindowLongPtr(window, ExtendedStyleIndex);

        // Compare only the border bits we own. WS_EX_TOPMOST is expected to change
        // as focus changes; comparing the entire style caused an endless remove/add
        // cycle and made Windows bounce focus away from the game.
        if ((currentStyle.ToInt64() & BorderMask) != 0)
        {
            SetWindowLongPtr(window, StyleIndex,
                new IntPtr(currentStyle.ToInt64() & ~BorderMask));
            styleChanged = true;
        }
        if ((currentExtendedStyle.ToInt64() & ExtendedBorderMask) != 0)
        {
            SetWindowLongPtr(window, ExtendedStyleIndex,
                new IntPtr(currentExtendedStyle.ToInt64() & ~ExtendedBorderMask));
            styleChanged = true;
        }

        var monitor = MonitorFromWindow(window, MonitorNearest);
        var monitorInfo = new MonitorInfo { Size = Marshal.SizeOf<MonitorInfo>() };
        if (!GetMonitorInfo(monitor, ref monitorInfo)) return;
        if (!GetClientRect(window, out var client)) return;
        var clientOrigin = new Point { X = 0, Y = 0 };
        if (!ClientToScreen(window, ref clientOrigin)) return;

        var target = monitorInfo.Monitor;
        var width = target.Right - target.Left;
        var height = target.Bottom - target.Top;
        var boundsChanged = clientOrigin.X != target.Left || clientOrigin.Y != target.Top ||
                            client.Right - client.Left != width || client.Bottom - client.Top != height;
        if (!styleChanged && !boundsChanged) return;

        ApplyBorderlessBounds(window, zOrder, target, forceResizePulse: styleChanged);
        Log($"Corrected client drift from {client.Right - client.Left}x{client.Bottom - client.Top} " +
            $"at {clientOrigin.X},{clientOrigin.Y} to {width}x{height} at {target.Left},{target.Top}.");
    }

    private static void ApplyBorderlessBounds(IntPtr window, IntPtr zOrder, Rect target,
        bool forceResizePulse)
    {
        var width = target.Right - target.Left;
        var height = target.Bottom - target.Top;

        // A maximized bordered window can already have 1920x1080 outer bounds while
        // its drawable client remains 1904x1041. Removing the frame alone does not
        // reliably emit the WM_SIZE Unity uses to rebuild its UI canvas. A one-pixel
        // pulse guarantees a real resize before settling at the monitor dimensions.
        if (forceResizePulse)
        {
            SetWindowPos(window, zOrder, target.Left, target.Top,
                Math.Max(1, width - 1), Math.Max(1, height - 1), ApplyFlags);
            Thread.Sleep(80);
        }

        if (!SetWindowPos(window, zOrder, target.Left, target.Top, width, height, ApplyFlags))
            ThrowWin32("SetWindowPos");
    }

    private static bool KeyDown(int key) => (GetAsyncKeyState(key) & 0x8000) != 0;

    private static bool IsGameProcessFocused(IntPtr window)
    {
        var foreground = GetForegroundWindow();
        if (foreground == IntPtr.Zero) return false;
        GetWindowThreadProcessId(window, out var gameProcessId);
        GetWindowThreadProcessId(foreground, out var foregroundProcessId);
        return gameProcessId != 0 && gameProcessId == foregroundProcessId;
    }

    private static bool IsChatActivationClick(IntPtr window)
    {
        if (!TryGetCursorInClient(window, out var cursor, out var width, out var height)) return false;

        var scale = height / 1080.0;
        var chatTop = height - (int)Math.Round(155 * scale);
        var chatBottom = height - (int)Math.Round(65 * scale);

        return cursor.X >= 0 && cursor.X <= width * 0.65 &&
               cursor.Y >= chatTop && cursor.Y <= chatBottom;
    }

    private static bool IsChatInputClick(IntPtr window)
    {
        if (!TryGetCursorInClient(window, out var cursor, out var width, out var height)) return false;

        var scale = height / 1080.0;
        var left = (width / 2.0) - (290 * scale);
        var right = (width / 2.0) + (245 * scale);
        var top = height - (90 * scale);
        var bottom = height - (25 * scale);

        return cursor.X >= left && cursor.X <= right &&
               cursor.Y >= top && cursor.Y <= bottom;
    }

    private static bool IsChatBackClick(IntPtr window)
    {
        if (!TryGetCursorInClient(window, out var cursor, out var width, out var height)) return false;

        var scale = height / 1080.0;
        var targetX = (width / 2.0) - (380 * scale);
        var targetY = height - (62 * scale);

        return Math.Abs(cursor.X - targetX) <= 65 * scale &&
               Math.Abs(cursor.Y - targetY) <= 55 * scale;
    }

    private static bool TryGetCursorInClient(IntPtr window, out Point cursor, out int width, out int height)
    {
        cursor = default;
        width = 0;
        height = 0;
        if (!GetCursorPos(out cursor)) return false;
        if (!ScreenToClient(window, ref cursor)) return false;
        if (!GetClientRect(window, out var client)) return false;

        width = client.Right - client.Left;
        height = client.Bottom - client.Top;
        return true;
    }

    private static void ClickGameControl(IntPtr window, ControlTarget target)
    {
        if (!GetClientRect(window, out var client)) ThrowWin32("GetClientRect");
        var width = client.Right - client.Left;
        var height = client.Bottom - client.Top;
        var scale = height / 1080.0;

        var x = target == ControlTarget.Back
            ? (int)Math.Round((width / 2.0) - (380 * scale))
            : (int)Math.Round(width - (46 * scale));
        var y = target == ControlTarget.Back
            ? (int)Math.Round(height - (62 * scale))
            : (int)Math.Round(height - (50 * scale));

        var click = new Point { X = Math.Max(24, x), Y = Math.Max(24, y) };
        if (!ClientToScreen(window, ref click)) ThrowWin32("ClientToScreen");

        GetCursorPos(out var previous);
        if (!GetClipCursor(out var previousClip)) ThrowWin32("GetClipCursor");
        var clickClip = new Rect
        {
            Left = click.X,
            Top = click.Y,
            Right = click.X + 1,
            Bottom = click.Y + 1
        };

        if (!ClipCursor(ref clickClip)) ThrowWin32("ClipCursor");
        try
        {
            SetCursorPos(click.X, click.Y);
            Thread.Sleep(40);
            SetCursorPos(click.X, click.Y);
            mouse_event(LeftDown, 0, 0, 0, UIntPtr.Zero);
            Thread.Sleep(30);
            SetCursorPos(click.X, click.Y);
            mouse_event(LeftUp, 0, 0, 0, UIntPtr.Zero);
            Thread.Sleep(80);
        }
        finally
        {
            ClipCursor(ref previousClip);
            SetCursorPos(previous.X, previous.Y);
        }
        Log($"{target} clicked at client position {x},{y}.");
    }

    private static void ThrowWin32(string operation) =>
        throw new InvalidOperationException($"{operation} failed: {Marshal.GetLastWin32Error()}");

    private static void Log(string text) =>
        File.AppendAllText(LogPath, $"{DateTime.Now:s} {text}{Environment.NewLine}");

    private enum ControlTarget { Back, Map }

    private sealed class KeyLatch
    {
        private bool armed = true;
        private int releasedTicks;

        public bool Triggered(bool down, bool active)
        {
            if (down)
            {
                releasedTicks = 0;
                if (active && armed)
                {
                    armed = false;
                    return true;
                }
            }
            else if (!armed && ++releasedTicks >= 5)
            {
                armed = true;
                releasedTicks = 0;
            }
            return false;
        }
    }
}
