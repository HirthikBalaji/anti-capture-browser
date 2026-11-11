Add-Type -AssemblyName PresentationFramework
Add-Type -AssemblyName PresentationCore
Add-Type -AssemblyName WindowsBase

$NativeCode = @"
using System;
using System.Runtime.InteropServices;

public class Win32 {
    public const uint WDA_NONE = 0x00000000;
    public const uint WDA_MONITOR = 0x00000001;
    public const uint WDA_EXCLUDEFROMCAPTURE = 0x00000011;

    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool SetWindowDisplayAffinity(IntPtr hWnd, uint dwAffinity);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool GetWindowDisplayAffinity(IntPtr hWnd, out uint pdwAffinity);
}
"@
Add-Type -TypeDefinition $NativeCode

[xml]$xaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="Anti-Capture Protected Window" 
        Height="550" Width="750" 
        Background="#1E1E2E" 
        WindowStartupLocation="CenterScreen">
    <Grid Margin="16">
        <Grid.RowDefinitions>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="*"/>
        </Grid.RowDefinitions>

        <!-- Header Card -->
        <Border Grid.Row="0" Background="#282A36" CornerRadius="8" Padding="14" Margin="0,0,0,12">
            <StackPanel>
                <TextBlock Text="Anti-Capture Protected Window" FontSize="18" FontWeight="Bold" Foreground="#F8F8F2"/>
                <Border Name="BadgeBorder" Background="#213B2C" CornerRadius="4" Padding="8,4" HorizontalAlignment="Left" Margin="0,8,0,4">
                    <TextBlock Name="StatusText" Text="* GHOST MODE ACTIVE (Excluded from Screenshots and Recordings)" 
                               FontWeight="Bold" Foreground="#50FA7B" FontSize="12"/>
                </Border>
                <TextBlock Name="StatusDesc" Text="This window is 100% invisible to Snipping Tool, OBS, Discord, Zoom, Teams, and screen recorders."
                           Foreground="#A6ADC8" FontSize="11" TextWrapping="Wrap" Margin="0,4,0,0"/>
            </StackPanel>
        </Border>

        <!-- Controls / Buttons -->
        <StackPanel Grid.Row="1" Orientation="Horizontal" Margin="0,0,0,10">
            <Button Name="BtnGhost" Content="Ghost Mode (Invisible)" Background="#2E5339" Foreground="#50FA7B" FontWeight="Bold" Padding="12,6" Margin="0,0,8,0"/>
            <Button Name="BtnBlack" Content="Blackout Mode" Background="#4D3822" Foreground="#FFB86C" FontWeight="Bold" Padding="12,6" Margin="0,0,8,0"/>
            <Button Name="BtnNone" Content="Allow Capture (Off)" Background="#4A2424" Foreground="#FF5555" FontWeight="Bold" Padding="12,6" Margin="0,0,8,0"/>
            <Button Name="BtnTopmost" Content="Always on Top: OFF" Background="#36384A" Foreground="#F8F8F2" Padding="12,6" Margin="0,0,8,0"/>
        </StackPanel>

        <!-- Editor Area -->
        <Border Grid.Row="2" Background="#282A36" CornerRadius="8" Padding="12">
            <Grid>
                <Grid.RowDefinitions>
                    <RowDefinition Height="Auto"/>
                    <RowDefinition Height="*"/>
                </Grid.RowDefinitions>
                <TextBlock Grid.Row="0" Text="Confidential Text (Try taking a screenshot with Win + Shift + S):" 
                           Foreground="#BD93F9" FontWeight="SemiBold" Margin="0,0,0,8"/>
                <TextBox Grid.Row="1" Name="EditorBox" 
                         Background="#1E1E2E" Foreground="#F8F8F2" 
                         CaretBrush="#50FA7B"
                         FontFamily="Consolas" FontSize="14" 
                         AcceptsReturn="True" AcceptsTab="True" 
                         VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Auto"
                         TextWrapping="Wrap" Padding="8" BorderThickness="0"/>
            </Grid>
        </Border>
    </Grid>
</Window>
"@

$reader = (New-Object System.Xml.XmlNodeReader $xaml)
$window = [System.Windows.Markup.XamlReader]::Load($reader)

$badgeBorder = $window.FindName("BadgeBorder")
$statusText = $window.FindName("StatusText")
$statusDesc = $window.FindName("StatusDesc")
$btnGhost = $window.FindName("BtnGhost")
$btnBlack = $window.FindName("BtnBlack")
$btnNone = $window.FindName("BtnNone")
$btnTopmost = $window.FindName("BtnTopmost")
$editorBox = $window.FindName("EditorBox")

$editorBox.Text = @"
======================================================
  CONFIDENTIAL SECURE DESKTOP WINDOW
======================================================

Active Protection: SetWindowDisplayAffinity -> WDA_EXCLUDEFROMCAPTURE (0x11)

TEST IT RIGHT NOW:
 1. Press [Windows + Shift + S] to take a screenshot.
 2. Screen record with OBS, Zoom, Teams, or Discord.
 
RESULT:
 - This window will NOT appear in the capture at all!
 - Instead, whatever is behind this window will be captured.

Switch modes using the buttons above:
 - Ghost Mode (0x11): Invisible to screen capture
 - Blackout Mode (0x01): Solid black box in capture
 - Normal Mode (0x00): Capture enabled
"@

$window.Add_SourceInitialized({
    $helper = New-Object System.Windows.Interop.WindowInteropHelper($window)
    $hwnd = $helper.Handle
    [Win32]::SetWindowDisplayAffinity($hwnd, [Win32]::WDA_EXCLUDEFROMCAPTURE) | Out-Null
})

$btnGhost.Add_Click({
    $helper = New-Object System.Windows.Interop.WindowInteropHelper($window)
    [Win32]::SetWindowDisplayAffinity($helper.Handle, [Win32]::WDA_EXCLUDEFROMCAPTURE) | Out-Null
    $badgeBorder.Background = [System.Windows.Media.BrushConverter]::new().ConvertFromString("#213B2C")
    $statusText.Text = "* GHOST MODE ACTIVE (Excluded from Screenshots and Recordings)"
    $statusText.Foreground = [System.Windows.Media.BrushConverter]::new().ConvertFromString("#50FA7B")
    $statusDesc.Text = "This window is 100% invisible to Snipping Tool, OBS, Discord, Zoom, Teams, and screen recorders."
})

$btnBlack.Add_Click({
    $helper = New-Object System.Windows.Interop.WindowInteropHelper($window)
    [Win32]::SetWindowDisplayAffinity($helper.Handle, [Win32]::WDA_MONITOR) | Out-Null
    $badgeBorder.Background = [System.Windows.Media.BrushConverter]::new().ConvertFromString("#3D2D1E")
    $statusText.Text = "* BLACKOUT MODE ACTIVE (Captures as Black Box)"
    $statusText.Foreground = [System.Windows.Media.BrushConverter]::new().ConvertFromString("#FFB86C")
    $statusDesc.Text = "This window will show as a black box in screen captures and recordings."
})

$btnNone.Add_Click({
    $helper = New-Object System.Windows.Interop.WindowInteropHelper($window)
    [Win32]::SetWindowDisplayAffinity($helper.Handle, [Win32]::WDA_NONE) | Out-Null
    $badgeBorder.Background = [System.Windows.Media.BrushConverter]::new().ConvertFromString("#3D1E1E")
    $statusText.Text = "O UNPROTECTED (Normally Visible in Capture)"
    $statusText.Foreground = [System.Windows.Media.BrushConverter]::new().ConvertFromString("#FF5555")
    $statusDesc.Text = "Standard mode: window can be captured normally."
})

$btnTopmost.Add_Click({
    $window.Topmost = -not $window.Topmost
    if ($window.Topmost) {
        $btnTopmost.Content = "Always on Top: ON"
    } else {
        $btnTopmost.Content = "Always on Top: OFF"
    }
})

$window.ShowDialog() | Out-Null
