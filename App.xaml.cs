using System.Windows;

namespace DocumentTranslator
{
    public partial class App : Application
    {
        protected override void OnStartup(StartupEventArgs e)
        {
            base.OnStartup(e);
            
            // 设置全局异常处理
            this.DispatcherUnhandledException += (sender, args) =>
            {
                MessageBox.Show($"应用程序发生未处理的异常：\n{args.Exception.Message}", 
                              "错误", MessageBoxButton.OK, MessageBoxImage.Error);
                args.Handled = true;
            };
        }
    }
}
