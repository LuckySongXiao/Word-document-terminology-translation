using System.Collections.Generic;
using System.Threading.Tasks;

namespace DocumentTranslator.Services.Translation
{
    /// <summary>
    /// 翻译器接口，定义所有翻译器必须实现的方法
    /// </summary>
    public interface ITranslator
    {
        /// <summary>
        /// 翻译文本
        /// </summary>
        /// <param name="text">要翻译的文本</param>
        /// <param name="terminologyDict">术语词典</param>
        /// <param name="sourceLang">源语言代码，默认为中文(zh)</param>
        /// <param name="targetLang">目标语言代码，默认为英文(en)</param>
        /// <param name="prompt">可选的翻译提示词，用于指导翻译风格和质量</param>
        /// <returns>翻译后的文本</returns>
        Task<string> TranslateAsync(string text, Dictionary<string, string> terminologyDict = null, 
            string sourceLang = "zh", string targetLang = "en", string prompt = null);

        /// <summary>
        /// 获取可用的模型列表
        /// </summary>
        /// <returns>模型列表</returns>
        Task<List<string>> GetAvailableModelsAsync();

        /// <summary>
        /// 测试连接
        /// </summary>
        /// <returns>连接是否成功</returns>
        Task<bool> TestConnectionAsync();
    }
}
