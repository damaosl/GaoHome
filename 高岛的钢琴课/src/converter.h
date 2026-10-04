#pragma once
#include <string>
#include <functional>
#include "formats.h"

// 转换结果
struct ConvertResult {
    bool ok = false;
    std::wstring message;      // 结果或错误说明
    std::wstring output_path;  // 成功时的输出文件完整路径
};

// 进度回调：参数为进度提示文本（如 "转换中 00:01:23"）
using ProgressFn = std::function<void(const std::wstring&)>;

// 生成不冲突的输出路径（目标已存在则自动追加 _1、_2 …）
std::wstring make_output_path(const std::wstring& input,
                              const wchar_t* ext,
                              const std::wstring& out_dir);

// 同步执行「提取音轨并转码」（请在后台线程调用），
// 通过 on_progress 回传进度文本
ConvertResult convert_audio(const std::wstring& ffmpeg_path,
                            const std::wstring& input,
                            const AudioFormat& fmt,
                            const std::wstring& output,
                            const ProgressFn& on_progress);
