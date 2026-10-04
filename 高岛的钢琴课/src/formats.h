#pragma once

// 支持的输出音频格式定义
struct AudioFormat {
    const wchar_t* name;      // 界面显示名称
    const wchar_t* ext;       // 文件扩展名（不含点）
    const wchar_t* ff_args;   // ffmpeg 音频编码参数
};

// 五种可选格式（顺序即界面单选顺序）
static const AudioFormat kAudioFormats[] = {
    { L"MP3",  L"mp3",  L"-c:a libmp3lame -b:a 192k" },   // 有损，最通用
    { L"WAV",  L"wav",  L"-c:a pcm_s16le"          },     // 无损，未压缩
    { L"FLAC", L"flac", L"-c:a flac"               },     // 无损，压缩
    { L"M4A",  L"m4a",  L"-c:a aac -b:a 192k"      },     // 有损，苹果系
    { L"OGG",  L"ogg",  L"-c:a libvorbis -q:a 4"   },     // 有损，开源
};

constexpr int kFormatCount        = 5;
constexpr int kDefaultFormatIndex = 0; // 默认 MP3
