using System;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Threading;
using System.Windows.Media;
using Microsoft.Web.WebView2.Wpf;
using Newtonsoft.Json;

namespace JARVIS.Shell
{
    public partial class MainWindow : Window
    {
        private HttpClient _httpClient;
        private DispatcherTimer _statusTimer;
        private bool _isProcessing;
        private bool _isConnected = false;
        private readonly string _apiUrl = "http://localhost:50051";

        public MainWindow()
        {
            InitializeComponent();
            Loaded += MainWindow_Loaded;
            SetupStatusTimer();
        }

        private async void MainWindow_Loaded(object sender, RoutedEventArgs e)
        {
            try
            {
                // Initialize WebView2 for hologram
                await webView.EnsureCoreWebView2Async(null);
                
                string url = "http://localhost:5173";
                webView.CoreWebView2.Navigate(url);

                // Setup HTTP client
                _httpClient = new HttpClient();
                _httpClient.Timeout = TimeSpan.FromSeconds(10);

                connectionStatus.Text = "● Connecting...";
                connectionStatus.Foreground = new SolidColorBrush(Colors.Yellow);

                // Connect to Python HTTP server
                await ConnectToPythonServer();
            }
            catch (Exception ex)
            {
                AddChatMessage("🔴 System", $"Error: {ex.Message}", Colors.Red);
            }
        }

        private async Task ConnectToPythonServer()
        {
            try
            {
                var response = await _httpClient.GetAsync($"{_apiUrl}/health");
                
                if (response.IsSuccessStatusCode)
                {
                    _isConnected = true;
                    statusText.Text = "🟢 JARVIS Online";
                    connectionStatus.Text = "● Online";
                    connectionStatus.Foreground = new SolidColorBrush(Colors.LightGreen);
                    AddChatMessage("🔷 System", "Connected to JARVIS AI engine.", Colors.Cyan);
                }
                else
                {
                    _isConnected = false;
                    connectionStatus.Text = "● Offline";
                    connectionStatus.Foreground = new SolidColorBrush(Colors.Red);
                    AddChatMessage("⚠️ System", "Python server not responding. Please start the server.", Colors.Yellow);
                }
            }
            catch (Exception ex)
            {
                _isConnected = false;
                connectionStatus.Text = "● Offline";
                connectionStatus.Foreground = new SolidColorBrush(Colors.Red);
                AddChatMessage("⚠️ System", $"Cannot connect to Python server: {ex.Message}", Colors.Yellow);
            }
        }

        private void SetupStatusTimer()
        {
            _statusTimer = new DispatcherTimer();
            _statusTimer.Interval = TimeSpan.FromSeconds(10);
            _statusTimer.Tick += async (s, e) => {
                if (!_isConnected)
                {
                    await ConnectToPythonServer();
                }
            };
            _statusTimer.Start();
        }

        private void AddChatMessage(string sender, string message, Color color)
        {
            Dispatcher.Invoke(() =>
            {
                var border = new Border
                {
                    Background = new SolidColorBrush(Color.FromArgb(30, color.R, color.G, color.B)),
                    CornerRadius = new CornerRadius(8),
                    Padding = new Thickness(12, 8),
                    Margin = new Thickness(0, 0, 0, 8),
                    MaxWidth = 320,
                    HorizontalAlignment = sender == "User" ? HorizontalAlignment.Right : HorizontalAlignment.Left
                };

                var stack = new StackPanel();
                
                if (sender != "User")
                {
                    var nameText = new TextBlock
                    {
                        Text = sender,
                        Foreground = new SolidColorBrush(color),
                        FontSize = 11,
                        FontWeight = FontWeights.Bold,
                        Margin = new Thickness(0, 0, 0, 4)
                    };
                    stack.Children.Add(nameText);
                }

                var msgText = new TextBlock
                {
                    Text = message,
                    Foreground = new SolidColorBrush(Colors.White),
                    FontSize = 13,
                    TextWrapping = TextWrapping.Wrap
                };
                stack.Children.Add(msgText);

                border.Child = stack;
                chatMessages.Children.Add(border);

                // Scroll to bottom
                chatScrollViewer.ScrollToBottom();
            });
        }

        private async void SendMessage(string message)
        {
            if (string.IsNullOrWhiteSpace(message) || message == "Type a message...")
                return;

            // Clear input
            chatInput.Text = "";
            chatInput.IsEnabled = false;
            sendButton.IsEnabled = false;

            // Show user message
            AddChatMessage("User", message, Colors.LightBlue);

            if (!_isConnected)
            {
                AddChatMessage("⚠️ System", "Python server is offline. Please start the server.", Colors.Yellow);
                chatInput.IsEnabled = true;
                sendButton.IsEnabled = true;
                return;
            }

            _isProcessing = true;
            statusText.Text = "💭 Thinking...";

            try
            {
                // Send command to Python via HTTP
                var request = new
                {
                    command = message,
                    user_id = "desktop_user",
                    session_id = "default"
                };

                var json = JsonConvert.SerializeObject(request);
                var content = new StringContent(json, Encoding.UTF8, "application/json");

                var response = await _httpClient.PostAsync($"{_apiUrl}/command", content);
                var responseJson = await response.Content.ReadAsStringAsync();
                var result = JsonConvert.DeserializeObject<dynamic>(responseJson);

                // Show JARVIS response
                AddChatMessage("🤖 JARVIS", (string)result.response, Colors.Cyan);
                statusText.Text = "🟢 JARVIS Online";
            }
            catch (Exception ex)
            {
                AddChatMessage("❌ Error", ex.Message, Colors.Red);
                _isConnected = false;
                connectionStatus.Text = "● Offline";
                connectionStatus.Foreground = new SolidColorBrush(Colors.Red);
            }
            finally
            {
                _isProcessing = false;
                chatInput.IsEnabled = true;
                sendButton.IsEnabled = true;
                chatInput.Focus();
            }
        }

        // UI Events
        private void SendButton_Click(object sender, RoutedEventArgs e) => SendMessage(chatInput.Text);

        private void ChatInput_KeyDown(object sender, KeyEventArgs e)
        {
            if (e.Key == Key.Enter && Keyboard.Modifiers != ModifierKeys.Shift)
            {
                e.Handled = true;
                SendMessage(chatInput.Text);
            }
        }

        private void ChatInput_GotFocus(object sender, RoutedEventArgs e)
        {
            if (chatInput.Text == "Type a message...")
            {
                chatInput.Text = "";
                chatInput.Foreground = new SolidColorBrush(Colors.White);
            }
        }

        private void ChatInput_LostFocus(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrWhiteSpace(chatInput.Text))
            {
                chatInput.Text = "Type a message...";
                chatInput.Foreground = new SolidColorBrush(Color.FromRgb(100, 100, 100));
            }
        }

        private void TitleBar_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            if (e.ClickCount == 2) MaximizeButton_Click(sender, e);
            else this.DragMove();
        }

        private void MinimizeButton_Click(object sender, RoutedEventArgs e) => this.WindowState = WindowState.Minimized;
        private void MaximizeButton_Click(object sender, RoutedEventArgs e) => this.WindowState = this.WindowState == WindowState.Maximized ? WindowState.Normal : WindowState.Maximized;
        private void CloseButton_Click(object sender, RoutedEventArgs e) => Application.Current.Shutdown();
    }
}
